<template>
  <div class="timetable-grid-container-el">
    <h3 v-if="totalWeeks === 1 && actualWeekNumber">第 {{ actualWeekNumber }} 周课表</h3>
    <!-- Use ElTable for the grid -->
    <el-table
      :data="tableData"
      style="width: 100%"
      border
      stripe
      :empty-text="entries.length === 0 ? '暂无排课数据' : '当前周无课程安排'"
      :row-class-name="tableRowClassName"
      :cell-style="{ padding: '5px 0' }"
      :header-cell-style="{ background: '#f2f2f2', color: '#606266', padding: '8px 0', textAlign: 'center' }"
    >
      <!-- Column for Time Period -->
      <el-table-column label="时间/节次" width="110" fixed="left" align="center">
        <template #default="scope">
          <div class="period-info">
            <div class="period-number">第 {{ scope.row.periodInfo.number }} 节</div>
            <div class="period-time">{{ scope.row.periodInfo.start }} - {{ scope.row.periodInfo.end }}</div>
          </div>
        </template>
      </el-table-column>

      <!-- Columns for Days of the Week -->
      <el-table-column
        v-for="day in daysOrder"
        :key="day"
        :label="day"
        min-width="140"
        align="center"
      >
        <template #default="scope">
          <!-- scope.row[day] contains the array of entries for this period and day -->
          <div v-if="scope.row[day] && scope.row[day].length > 0" class="timetable-cell-content">
            <div v-for="(item, itemIndex) in scope.row[day]" :key="item.id || itemIndex" class="entry-item">
              <div><strong>{{ item.course_name }}</strong></div>

              <!-- Conditional display based on viewType -->
              <div v-if="shouldShow(viewType, 'teacher', item.teacher_name)" class="detail-item teacher-name">
                  <el-icon><User /></el-icon> {{ item.teacher_name }}
              </div>
              <div v-if="shouldShow(viewType, 'major', item.major_name)" class="detail-item major-name">
                  <el-icon><Collection /></el-icon> {{ item.major_name }}
              </div>
              <div v-if="item.classroom_name" class="detail-item classroom-name">
                  <el-icon><Location /></el-icon> {{ item.classroom_name }}
              </div>
              <div class="detail-item course-type" v-if="item.course_type">
                  <el-icon><PriceTag /></el-icon> {{ item.course_type }}
              </div>

              <!-- Separator for multiple entries -->
              <el-divider v-if="scope.row[day].length > 1 && itemIndex < scope.row[day].length - 1" />
            </div>
          </div>
          <!-- Empty cell styling (can be implicit or use a placeholder) -->
          <div v-else class="timetable-cell-empty">&nbsp;</div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineProps, nextTick } from 'vue';
import { ElTable, ElTableColumn, ElIcon, ElDivider, ElEmpty } from 'element-plus';
// Import necessary icons
import { User, Collection, Location, PriceTag } from '@element-plus/icons-vue';

// --- Props ---
const props = defineProps({
  entries: {
    type: Array,
    required: true,
    default: () => []
  },
  totalWeeks: {
    type: Number,
    default: 1
  },
  actualWeekNumber: {
     type: Number,
     default: 1
  },
  viewType: {
    type: String,
    default: 'major',
    validator: (value) => ['major', 'teacher', 'student', 'admin'].includes(value)
  }
});

// --- Constants ---
const daysOrder = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
// Default times (improved fallback)
const defaultTimes = [
    { start: '08:00', end: '09:30' }, { start: '09:40', end: '11:10' }, // 1-2
    { start: '13:30', end: '15:00' }, { start: '15:10', end: '16:40' }, // 3-4

];

// --- Computed Properties ---

// 1. Processed Periods: Determine unique periods and their start/end times from entries
const processedPeriods = computed(() => {
    const periodMap = {};
    let maxPeriodNum = 0;
    props.entries.forEach(entry => {
        if (entry.period) {
             const periodNum = Number(entry.period);
             maxPeriodNum = Math.max(maxPeriodNum, periodNum);
            if (!periodMap[periodNum] && entry.start_time && entry.end_time) {
                // Only store the first valid time found for a period
                periodMap[periodNum] = {
                    start: entry.start_time.substring(0, 5), // HH:MM
                    end: entry.end_time.substring(0, 5)      // HH:MM
                };
            }
        }
    });

    // Ensure all periods up to the maximum found are included, using defaults if necessary
    const allPeriods = {};
    // Determine the highest period number to display (either from data or default 12)
    const highestPeriodToDisplay = Math.max(maxPeriodNum, defaultTimes.length); // Or a fixed number like 12

    for (let p = 1; p <= highestPeriodToDisplay; p++) {
        allPeriods[p] = periodMap[p] || defaultTimes[p - 1] || { start: '??:??', end: '??:??' };
    }
    return allPeriods;
});

// 2. Intermediate Processed Timetable (Lookup Structure)
// Structure: { weekIndex: { dayOfWeek: { period: [entry, entry, ...] } } }
const processedTimetableLookup = ref({});

watch(() => [props.entries, props.actualWeekNumber, props.totalWeeks], () => {
    console.log(`WATCH: Re-processing timetable lookup for week ${props.actualWeekNumber}`);
    const tempLookup = {};
    const weekIndex = props.actualWeekNumber - 1; // 0-based index

    // Initialize structure only for the current week being displayed
    if (weekIndex >= 0) {
        tempLookup[weekIndex] = {};
        daysOrder.forEach(day => {
            tempLookup[weekIndex][day] = {};
            // Initialize periods within the day based on processedPeriods keys
            Object.keys(processedPeriods.value).forEach(periodNum => {
                 tempLookup[weekIndex][day][periodNum] = []; // Initialize as empty array
            });
        });

        props.entries.forEach(entry => {
            // Filter entries for the *current* week only
            if (entry.week_number && Number(entry.week_number) === props.actualWeekNumber && entry.day_of_week && entry.period) {
                const day = entry.day_of_week;
                const period = entry.period;

                // Check if the structure exists (should exist due to initialization)
                if (tempLookup[weekIndex] && tempLookup[weekIndex][day] && tempLookup[weekIndex][day][period]) {
                    tempLookup[weekIndex][day][period].push(entry);
                } else {
                     console.warn('TimetableGridDisplay: Mismatch in structure for entry:', entry, `Target: W${weekIndex}, D${day}, P${period}`);
                }
            }
        });

        // Optional: Sort entries within each cell
        if (tempLookup[weekIndex]) {
            daysOrder.forEach(day => {
                 if (tempLookup[weekIndex][day]) {
                     Object.keys(tempLookup[weekIndex][day]).forEach(period => {
                         // Sort by course name, for example
                         tempLookup[weekIndex][day][period].sort((a, b) =>
                             (a.course_name || '').localeCompare(b.course_name || '')
                         );
                     });
                 }
            });
        }
    } else {
         console.warn(`Invalid actualWeekNumber: ${props.actualWeekNumber}`);
    }


    processedTimetableLookup.value = tempLookup;
     console.log('Processed Timetable Lookup Structure:', JSON.parse(JSON.stringify(processedTimetableLookup.value)));
}, { immediate: true, deep: true }); // Deep might be overkill if entries refs don't change


// 3. Table Data: Transform the lookup structure into row-based data for ElTable
const tableData = computed(() => {
  console.log(`COMPUTED: Generating tableData for week ${props.actualWeekNumber}`);
  const data = [];
  const weekIndex = props.actualWeekNumber - 1;
  const currentWeekLookup = processedTimetableLookup.value[weekIndex];

  // Iterate through the determined periods to create rows
  for (const periodNum in processedPeriods.value) {
    const periodInfo = {
      number: periodNum,
      ...processedPeriods.value[periodNum] // { start, end }
    };

    const row = {
      periodInfo: periodInfo
    };

    // Populate data for each day in this period (row)
    daysOrder.forEach(day => {
      // Get entries from the lookup structure for this specific week, day, and period
      row[day] = (currentWeekLookup && currentWeekLookup[day] && currentWeekLookup[day][periodNum])
                 ? currentWeekLookup[day][periodNum]
                 : []; // Default to empty array if no data found
    });

    data.push(row);
  }
   console.log('Generated tableData:', JSON.parse(JSON.stringify(data)));
  return data;
});


// --- Methods ---

// Helper to decide whether to show teacher/major based on viewType
const shouldShow = (viewType, infoType, value) => {
    if (!value) return false; // Don't show if value is empty
    switch (viewType) {
        case 'admin':
        case 'major': // Major view shows both teacher and major
            return true;
        case 'teacher': // Teacher view shows major, but not own name
            return infoType === 'major';
        case 'student': // Student view shows teacher, but not own major
             return infoType === 'teacher';
        default:
            return false;
    }
};

// Add class to rows for potential styling (e.g., odd/even) - ElTable stripe does this too
const tableRowClassName = ({ row, rowIndex }) => {
  if (rowIndex % 2 === 1) {
    return 'warning-row'; // Example class name from Element Plus docs
  }
  return '';
};

</script>

<style scoped>
.timetable-grid-container-el {
  /* Container styling if needed */
   margin: 15px 0;
}

.period-info {
  line-height: 1.4;
  padding: 5px 0; /* Add some vertical padding */
}

.period-number {
  font-weight: bold;
  font-size: 0.9em;
}

.period-time {
  font-size: 0.8em;
  color: #666;
}

.timetable-cell-content {
  padding: 5px;
  text-align: center; /* Align text left within cells */
  min-height: 70px; /* Ensure minimum height */
  font-size: 1.05em; /* Slightly smaller font size for cell content */
  line-height: 1.5;
}
.entry-item > div {
     margin-bottom: 3px; /* Space between lines in an entry */
}
.entry-item > div:last-child {
     margin-bottom: 0;
}

.timetable-cell-empty {
  min-height: 70px; /* Match content height */
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc; /* Optional: subtle color for empty cells */
}

.detail-item {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px; /* Space between icon and text */
    color: #333; /* Default color for details */
}
.detail-item .el-icon {
    font-size: 1.1em; /* Slightly larger icon */
}


.teacher-name { color: #007bff; } /* Example color */
.major-name { color: #28a745; } /* Example color */
.classroom-name { color: #dc3545; } /* Example color */
.course-type { color: #6c757d; font-style: italic; } /* Example style */


/* Element Plus Divider customization */
.timetable-cell-content .el-divider--horizontal {
    margin: 8px 0; /* Adjust spacing around divider */
    border-top: 1px dashed #dcdfe6;
}

h3 {
    text-align: center;
    margin-bottom: 15px;
    color: #333;
    font-weight: 600;
}

/* Style for odd/even rows if using row-class-name (optional, stripe does similar) */
/*
.el-table .warning-row {
  background: oldlace;
}
*/
</style>
