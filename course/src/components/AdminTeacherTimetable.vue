<template>
  <div class="timetable-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>查询教师课表</span>
        </div>
      </template>

      <!-- Controls -->
      <el-form :inline="true" class="controls-form" @submit.prevent="fetchTeacherTimetable">
        <!-- 学期选择 -->
        <el-form-item label="选择学期:">
          <el-select
            v-model="selectedSemesterId"
            placeholder="请选择学期"
            @change="onSemesterChange"
            clearable
            filterable
            style="width: 240px;"
          >
            <el-option
              v-for="semester in semesters"
              :key="semester.id"
              :label="`${semester.name} ${semester.total_weeks ? `(共${semester.total_weeks}周)` : ''}`"
              :value="semester.id"
            />
          </el-select>
        </el-form-item>

        <!-- 教师选择 -->
        <el-form-item label="选择教师:">
          <el-select
            v-model="selectedTeacherId"
            placeholder="请选择教师"
            @change="clearTimetableAndWeek"
            :disabled="!selectedSemesterId"
            clearable
            filterable
            style="width: 150px;"
          >
            <el-option
              v-for="teacher in teachers"
              :key="teacher.id"
              :label="teacher.name"
              :value="teacher.id"
            />
          </el-select>
        </el-form-item>

        <!-- 周数选择 -->
        <el-form-item label="选择周次:">
          <el-select
            v-model="selectedWeek"
            placeholder="请选择周次"
            :disabled="!selectedSemesterId || availableWeeks.length === 0"
            clearable
            style="width: 150px;"
          >
            <!-- No "All Weeks" option -->
            <el-option
              v-for="week in availableWeeks"
              :key="week"
              :label="`第 ${week} 周`"
              :value="week"
            />
          </el-select>
        </el-form-item>

        <!-- Action Buttons -->
        <el-form-item>
          <el-button
            type="primary"
            @click="fetchTeacherTimetable"
            :disabled="!selectedSemesterId || !selectedTeacherId || isLoading"
            :loading="isLoading"
            :icon="Search"
          >
            {{ isLoading ? '查询中...' : '查询课表' }}
          </el-button>
          <el-button
            type="success"
            @click="exportTeacherTimetable"
            :disabled="!selectedSemesterId || !selectedTeacherId || allFetchedEntries.length === 0 || isLoadingExport"
            :loading="isLoadingExport"
            :icon="Download"

          >
            {{ isLoadingExport ? '导出中...' : '导出学期Excel' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- Status Messages -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage=''" class="status-alert"/>

      <!-- Timetable Display Area -->
       <div v-loading="isLoading" class="timetable-container">
           <div v-if="!isLoading && displayedEntries.length > 0 && selectedWeek" class="timetable-display-area">
               <TimetableGridDisplay
                   :entries="displayedEntries"
                   :totalWeeks="1"
                   :actualWeekNumber="selectedWeek"
                   viewType="teacher"
               />
           </div>

           <!-- No data messages -->
            <el-alert v-if="!isLoading && hasSearched && allFetchedEntries.length > 0 && displayedEntries.length === 0 && selectedWeek && !errorMessage"
                :title="`该教师在此学期、第 ${selectedWeek} 周没有排课数据。请尝试选择其他周次。`"
                type="info"
                show-icon
                :closable="false"
                class="status-alert"/>

           <el-empty
              v-if="!isLoading && hasSearched && allFetchedEntries.length === 0 && !errorMessage"
              description="未查询到该教师在此学期的任何排课数据" />

           <el-empty
              v-if="!isLoading && !hasSearched && !errorMessage && (!selectedSemesterId || !selectedTeacherId)"
              description="请先选择学期和教师，然后点击查询" />

             <el-empty
                v-if="!isLoading && hasSearched && allFetchedEntries.length > 0 && !selectedWeek && !errorMessage"
                description="请选择周次以查看课表" />
       </div>

    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import axios from 'axios';
import TimetableGridDisplay from './TimetableGridDisplay.vue'; // Assuming this is adapted or compatible
import {
    ElCard, ElForm, ElFormItem, ElSelect, ElOption, ElButton, ElAlert, ElEmpty, ElLoading, ElMessage, ElMessageBox
} from 'element-plus';
import { Search, Download } from '@element-plus/icons-vue';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// --- State ---
const semesters = ref([]);
const teachers = ref([]);
const selectedSemesterId = ref(null); // Use null for clearable selects
const selectedTeacherId = ref(null); // Use null for clearable selects
const selectedWeek = ref(1); // Default to week 1
const allFetchedEntries = ref([]); // Stores all entries for the semester/teacher
const displayedEntries = ref([]); // Entries filtered for the selected week

// --- Status Flags ---
const isLoading = ref(false);
const isLoadingExport = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false); // Track if a search has been performed

// --- Computed Properties ---
const selectedSemesterData = computed(() => {
    if (!selectedSemesterId.value) return null;
    // Ensure comparison is correct (assuming IDs are numbers)
    return semesters.value.find(s => s.id === Number(selectedSemesterId.value));
});

const availableWeeks = computed(() => {
  const total = selectedSemesterData.value?.total_weeks;
  if (total && total > 0) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  return [];
});

// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchSemesters();
  await fetchTeachers();
});

// --- Watchers ---
watch(selectedWeek, (newWeek) => {
    // console.log('Selected week changed to:', newWeek);
    // Always filter when week changes, even if newWeek is null/undefined (will clear displayedEntries)
    filterTimetableForWeek();
});

watch(allFetchedEntries, () => {
    // console.log('allFetchedEntries updated. Total entries:', allFetchedEntries.value.length);
    // When fetched data changes, filter based on the *current* selectedWeek
    filterTimetableForWeek();
}, { deep: true }); // Use deep watch cautiously if entry structure is complex


// --- Methods ---

const fetchSemesters = async () => {
  // No loading indicator here as it's initial setup
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data.map(s => ({
        ...s,
        id: Number(s.id),
        total_weeks: Number(s.total_weeks) || 18 // Provide a fallback
    }));
  } catch (error) {
    ElMessage.error('获取学期列表失败。');
    console.error(error);
  }
};

const fetchTeachers = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/teachers-list`);
    teachers.value = response.data.map(t => ({
        ...t,
        id: Number(t.id)
    }));
  } catch (error) {
    ElMessage.error('获取教师列表失败。');
    console.error(error);
  }
};

// Clear timetable data and reset week selection
const clearTimetableAndWeek = () => {
    allFetchedEntries.value = [];
    // displayedEntries will be cleared by the watcher on allFetchedEntries
    errorMessage.value = '';
    hasSearched.value = false;
    selectedWeek.value = 1; // Reset week to 1 when teacher changes
};

// Handle semester change
const onSemesterChange = (newSemesterId) => {
    allFetchedEntries.value = [];
    errorMessage.value = '';
    hasSearched.value = false;
    selectedTeacherId.value = null; // Force re-selection of teacher

    // Reset week selection based on new semester's available weeks
    if (newSemesterId && availableWeeks.value.length > 0) {
        selectedWeek.value = 1; // Default to week 1 if weeks are available
    } else {
        selectedWeek.value = null; // No weeks available or semester cleared
    }
    // displayedEntries will be cleared by the watcher on allFetchedEntries/selectedWeek
};


// Filter displayed entries based on selected week
const filterTimetableForWeek = () => {
    // console.log(`Filtering timetable for week: ${selectedWeek.value}`);
    if (!allFetchedEntries.value || allFetchedEntries.value.length === 0) {
        displayedEntries.value = [];
        // console.log('No allFetchedEntries to filter.');
        return;
    }

    const weekToDisplay = Number(selectedWeek.value);

    // If week is not a valid number or not selected, clear display
    if (isNaN(weekToDisplay) || selectedWeek.value === null || selectedWeek.value === undefined) {
         displayedEntries.value = [];
        // console.warn(`Selected week ${selectedWeek.value} is invalid or not selected.`);
        return;
    }

    // Filter for the specific week
    displayedEntries.value = allFetchedEntries.value.filter(entry => entry.week_number === weekToDisplay);

    // console.log(`Filtered entries for week ${weekToDisplay}: ${displayedEntries.value.length}`);

    // Log if filtering resulted in empty for a specific week after searching
     if (displayedEntries.value.length === 0 && hasSearched.value && selectedWeek.value) {
         // console.warn(`No entries found for week ${weekToDisplay} after filtering.`);
     }
};


// Fetch timetable data for the selected semester and teacher
const fetchTeacherTimetable = async () => {
  if (!selectedSemesterId.value || !selectedTeacherId.value) {
      ElMessage.warning('请先选择学期和教师。');
      return;
  }

  isLoading.value = true;
  errorMessage.value = '';
  allFetchedEntries.value = []; // Clear previous results
  hasSearched.value = true; // Mark that a search was attempted

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/teacher/${selectedTeacherId.value}/semester/${selectedSemesterId.value}`
    );
    allFetchedEntries.value = Array.isArray(response.data) ? response.data : [];
    // console.log(`Fetched ${allFetchedEntries.value.length} total entries for the semester.`);

    // After fetch, the watcher on allFetchedEntries will trigger filtering.
    // Ensure selectedWeek is valid, default to 1 if needed and possible.
    if (allFetchedEntries.value.length > 0) {
        if (!availableWeeks.value.includes(Number(selectedWeek.value))) {
             selectedWeek.value = availableWeeks.value.length > 0 ? 1 : null;
        } else if (selectedWeek.value === null || selectedWeek.value === undefined){
            // If week was cleared before search, set it back to 1
             selectedWeek.value = availableWeeks.value.length > 0 ? 1 : null;
        }
        // If selectedWeek is already valid, the filter will just use it.
    } else {
        // No data fetched, ensure display is clear
        displayedEntries.value = [];
    }


  } catch (error) {
    errorMessage.value = `获取教师课表失败: ${error.response?.data?.message || error.message}`;
    console.error(error);
    allFetchedEntries.value = []; // Clear on error
    // displayedEntries cleared by watcher
  } finally {
    isLoading.value = false;
  }
};

// Export timetable to Excel
const exportTeacherTimetable = async () => {
  if (!selectedSemesterId.value || !selectedTeacherId.value) {
      ElMessage.warning('请先选择学期和教师。');
      return;
  }
   if (allFetchedEntries.value.length === 0) {
       ElMessage.info('没有课表数据可供导出。');
       return;
   }

  isLoadingExport.value = true;
  errorMessage.value = ''; // Clear previous errors
  const loadingInstance = ElLoading.service({ text: '正在生成Excel文件...' });

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/export/teacher/${selectedTeacherId.value}/semester/${selectedSemesterId.value}`,
      { responseType: 'blob' }
    );

    const blob = new Blob([response.data], { type: response.headers['content-type'] || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Extract filename from content-disposition header if available
    const contentDisposition = response.headers['content-disposition'];
    let fileName = `教师课表_导出.xlsx`; // Default filename
     const teacherName = teachers.value.find(t => t.id === Number(selectedTeacherId.value))?.name || `ID${selectedTeacherId.value}`;
     const semesterName = semesters.value.find(s => s.id === Number(selectedSemesterId.value))?.name || `ID${selectedSemesterId.value}`;
     fileName = `教师课表_${teacherName}_${semesterName}_(全学期).xlsx`; // Improved default

    if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename\*?=['"]?([^'";]+)['"]?/);
        if (fileNameMatch && fileNameMatch[1]) {
             fileName = decodeURIComponent(fileNameMatch[1]);
        }
    }

    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    ElMessage.success('Excel文件已开始下载。');

  } catch (error) {
    errorMessage.value = `导出Excel失败: ${error.response?.data?.message || '无法连接服务器或文件生成出错。'}`;
    console.error('Export error:', error);
    // Attempt to read error message from blob if backend returns JSON error in blob
    if (error.response && error.response.data instanceof Blob && error.response.data.type.includes('application/json')) {
        try {
            const errorJson = JSON.parse(await error.response.data.text());
            errorMessage.value = `导出Excel失败: ${errorJson.message || '文件生成出错。'}`;
        } catch (parseError) {
             // Ignore if blob isn't valid JSON
        }
    }
  } finally {
    isLoadingExport.value = false;
    loadingInstance.close();
  }
};
</script>

<style scoped>
.timetable-view {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 2em;

  font-weight: bold;
}
.controls-form {
  display: flex;
  flex-wrap: wrap; /* Allow wrapping on smaller screens */
  gap: 15px; /* Spacing between form items */
  margin-bottom: 20px;
  align-items: flex-end; /* Align items to the bottom line */
}
.controls-form .el-form-item {
  margin-bottom: 0; /* Override default margin for inline form */
   /* Let flex gap handle spacing */
   margin-right: 0 !important;
}
.status-alert {
    margin-top: 15px;
    margin-bottom: 15px;
}

.timetable-container {
    margin-top: 20px;
    min-height: 200px; /* Ensure container has height for v-loading */
}

.timetable-display-area {
  margin-top: 0; /* No extra margin needed if container has it */
}

/* Ensure loading mask covers the content area */
.timetable-container .el-loading-mask {
    z-index: 10; /* Ensure it's above content */
}

/* Make Empty state centered */
.timetable-container .el-empty {
    padding: 40px 0; /* Add some padding */
}

</style>
