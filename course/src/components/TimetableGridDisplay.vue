<template>
  <div class="timetable-grid-container-el">
    <!-- Use ElEmpty for no data state -->
    <el-empty v-if="!tableData || tableData.length === 0" description="没有课表数据可以显示" />

    <!-- Use ElTable for the grid -->
    <el-table
      v-else
      :data="tableData"
      style="width: 100%"
      border
      stripe
      :cell-style="cellStyle"
      :header-cell-style="{ background: '#e9ecef', color: '#333', textAlign: 'center' }"
    >
      <!-- Time Column (Fixed) -->
      <el-table-column
        prop="time"
        label="时间"
        width="100"
        align="center"
        fixed="left"
      />

      <!-- Day Columns (Dynamic) -->
      <el-table-column
        v-for="day in daysOrder"
        :key="day"
        :label="day"
        :prop="day"
        min-width="140"
        align="center"
      >
        <template #default="scope">
          <!-- scope.row contains the data for the current period (row) -->
          <!-- scope.row[day] contains the array of courses for this specific cell -->
          <div v-if="scope.row[day] && scope.row[day].length > 0" class="timetable-cell-content-el">
            <div v-for="(item, index) in scope.row[day]" :key="item.id || index" class="course-item">
               <!-- Add a separator line if more than one course in the slot -->
               <el-divider v-if="index > 0" style="margin: 4px 0;" />
               <div><strong>{{ item.course_name }}</strong></div>
               <div v-if="viewType === 'major'">{{ item.teacher_name }}</div>
               <div v-if="viewType === 'teacher'" class="detail-text">({{ item.major_name }})</div>
               <div class="detail-text">@ {{ item.classroom_name }}</div>
               <div class="course-type-el">({{ item.course_type }})</div>
            </div>
          </div>
          <!-- Optional: Render empty div or specific style if no data -->
          <!-- <div v-else>&nbsp;</div> -->
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
// Import Element Plus components used in the template
import { ElTable, ElTableColumn, ElEmpty, ElDivider } from 'element-plus';

const props = defineProps({
  entries: { type: Array, required: true },
  totalWeeks: { type: Number, required: true, default: 1 }, // Still needed if week navigation exists elsewhere
  viewType: { type: String, default: 'major' } // 'major', 'teacher'
});

// --- State and Constants ---
const currentWeek = ref(1); // Keep for potential external navigation logic compatibility
const daysOrder = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const periodsOrder = ref([1, 2, 3, 4, 5]); // Default periods

// --- Watchers ---
// Watch totalWeeks (if external navigation updates it)
watch(() => props.totalWeeks, (newVal) => {
    if (newVal > 0 && currentWeek.value > newVal) {
        currentWeek.value = newVal;
    } else if (newVal === 0 && currentWeek.value !== 1) {
        currentWeek.value = 1;
    } else if (newVal > 0 && currentWeek.value === 0){
        currentWeek.value = 1;
    }
}, { immediate: true });

// --- Computed Properties ---

// 1. Process entries into a structured object (similar to original logic)
//    Result: { 周一: { 1: [course1, course2], 2: null, ... }, 周二: {...} }
const processedTimetableForWeek = computed(() => {
  console.log("GridDisplay (El+): Recalculating processedTimetableForWeek. Entries:", props.entries.length);
  if (!props.entries || props.entries.length === 0) {
      console.log("GridDisplay (El+): No entries.");
      return {}; // Return empty object if no entries
  }

  // Initialize the structure for the current week
  const weekTimetable = daysOrder.reduce((acc, day) => {
      acc[day] = periodsOrder.value.reduce((pAcc, period) => {
        pAcc[period] = null; // Initialize cell as null initially
        return pAcc;
      }, {});
      return acc;
    }, {});

  let maxPeriodFound = 0;

  props.entries.forEach((entry) => {
    // We assume entries are pre-filtered for the correct week if needed externally
    // Or, if handling multiple weeks here, filter by `entry.week_number === currentWeek.value`
    const dayKey = entry.day_of_week;
    const period = entry.period;

    if (daysOrder.includes(dayKey) && typeof period === 'number' && period > 0 && periodsOrder.value.includes(period)) {
        if (!weekTimetable[dayKey]) {
             weekTimetable[dayKey] = {}; // Should not happen if initialized correctly
        }
        if (weekTimetable[dayKey][period] === null) {
             weekTimetable[dayKey][period] = []; // Initialize as array if it's the first entry for this slot
        }

        // Add the course details
        weekTimetable[dayKey][period].push({
            id: entry.id, // IMPORTANT: Make sure entries have a unique ID
            course_name: entry.course_name,
            teacher_name: entry.teacher_name,
            major_name: entry.major_name,
            classroom_name: entry.classroom_name,
            course_type: entry.course_type,
            // Keep debug info if needed
            debug_week_number: entry.week_number,
            debug_day_string: entry.day_of_week,
            debug_period_number: entry.period
        });

        if (period > maxPeriodFound) maxPeriodFound = period;

    } else {
         console.warn(`GridDisplay (El+): Skipping entry due to invalid day ('${dayKey}') or period (${period}):`, entry);
    }
  });

   // Optional: Dynamically adjust periodsOrder based on found data
   if (maxPeriodFound > periodsOrder.value.length) {
       console.log(`GridDisplay (El+): Max period ${maxPeriodFound} found, updating periodsOrder.`);
       periodsOrder.value = Array.from({length: maxPeriodFound}, (_, i) => i + 1);
       // Note: This might cause a re-computation, which is usually fine.
   }


  console.log("GridDisplay (El+): Processed week data:", JSON.parse(JSON.stringify(weekTimetable)));
  return weekTimetable;
});

// 2. Transform the processed data into row-based format for ElTable
//    Result: [ { time: '1-2节', 周一: [course], 周二: null, ... }, { time: '3-4节', ...} ]
const tableData = computed(() => {
    const weekData = processedTimetableForWeek.value;
    if (Object.keys(weekData).length === 0) {
        return []; // Return empty array if no processed data
    }

    return periodsOrder.value.map(period => {
        const row = {
            time: formatPeriod(period) // Add the formatted time label for the first column
        };
        daysOrder.forEach(day => {
            // Get the array of courses (or null) for this day/period
            row[day] = weekData[day]?.[period] || null; // Use null if day or period doesn't exist
        });
        return row;
    });
});


// --- Methods ---

// Format period number to display string (e.g., 1 -> '1-2节')
const formatPeriod = (period) => {
  // Adjust this map according to your actual period definitions
  const periodMap = { 1: "1-2节", 2: "3-4节", 3: "5-6节", 4: "7-8节", 5: "9-10节" };
  return periodMap[period] || `第${period}大节`;
};

// Style function for table cells (optional, e.g., fixed height)
const cellStyle = ({ row, column, rowIndex, columnIndex }) => {
  // Example: Set minimum height for content cells
  if (columnIndex > 0) { // Skip the 'Time' column
      return { padding: '8px 5px', height: '100px', verticalAlign: 'top' }; // Adjust height as needed
  }
  // Style for the 'Time' column
  return { padding: '8px 5px', fontWeight: 'bold', verticalAlign: 'middle'};
};

// prevWeek/nextWeek methods (keep if navigation controls are outside this component)
// const prevWeek = () => { if (currentWeek.value > 1) currentWeek.value--; };
// const nextWeek = () => { if (currentWeek.value < props.totalWeeks) currentWeek.value++; };

</script>

<style scoped>
.timetable-grid-container-el {
  font-family: Arial, sans-serif;
  padding: 15px; /* Add some padding around the table */
}

/* Style for the content within each cell */
.timetable-cell-content-el {
  font-size: 1.08em; /* Slightly larger font */
  line-height: 1.4;
  text-align: center; /* Align text left within the cell */
  padding: 2px;
}

.course-item {
    margin-bottom: 4px; /* Space between items if multiple in one slot */
}

/* Reduce default divider margin */
.el-divider--horizontal {
    margin: 4px 0 !important;
}

.detail-text {
    color: #555;
    font-size: 1.0em; /* Smaller text for details */
}

.course-type-el {
    font-style: italic;
    color: #777;
    font-size: 1.0em;
}

/* Optional: Style el-empty */
.el-empty {
  padding: 40px 0;
}

/* Override default ElTable cell padding if needed, otherwise use cell-style */
/*
:deep(.el-table td.el-table__cell),
:deep(.el-table th.el-table__cell) {
    padding: 6px 4px !important;
}
*/
</style>
