<template>
  <div class="page-content">
    <el-card shadow="never" class="main-card">
       <template #header>
          <div class="card-header">
             <span>教师排课要求管理</span>
          </div>
       </template>

      <!-- Request Section -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <h3>提出新的时间偏好</h3>
        </template>
        <p>您可以在这里提出希望 <strong>避免</strong> 安排课程的时间段。请在管理员设置排课计划前提交。</p>
        <el-button type="success" @click="openRequestModal" :icon="Plus">
          提出新的时间偏好
        </el-button>
      </el-card>

      <!-- Preferences List Section -->
      <el-card shadow="hover" class="section-card" v-loading="isPreferencesLoading" element-loading-text="加载偏好列表中...">
        <template #header>
           <h3>我已提交的时间偏好</h3>
        </template>

        <el-alert v-if="preferencesError" :title="preferencesError" type="error" show-icon :closable="false" />

        <el-empty v-else-if="teacherPreferences.length === 0" description="您还没有提交任何时间偏好" />

        <div v-else class="preferences-list">
          <el-card v-for="pref in teacherPreferences" :key="pref.id" class="preference-item" shadow="never">
            <div class="preference-content">
                <div class="preference-main-info">
                    <span class="semester-name">{{ pref.semester_name }}</span>
                    <span class="timeslot-info">
                        {{ pref.day_of_week_display }} 第 {{ pref.period }} 节 ({{ pref.start_time }} - {{ pref.end_time }})
                    </span>
                    <el-tag :type="getPreferenceTypeTag(pref.preference_type)" size="small" effect="light" style="margin-left: 10px;">
                       {{ pref.preference_type_display }}
                    </el-tag>
                </div>
                <div class="preference-status-time">
                    <span class="preference-status">
                       状态: <el-tag :type="getStatusTagType(pref.status)" size="small" effect="plain">{{ pref.status_display }}</el-tag>
                    </span>
                     <span class="preference-timestamps">
                         提交于: {{ pref.created_at_formatted }}
                     </span>
                </div>
                <div v-if="pref.reason" class="preference-reason">
                    原因: <span>{{ pref.reason }}</span>
                </div>
            </div>
             <div class="preference-actions">
                <el-button
                   type="danger"
                   :icon="Delete"
                   size="small"
                   circle
                   plain
                   @click="confirmDeletePreference(pref.id)"
                   :loading="isDeleting[pref.id]"
                   title="删除此偏好"
                />
             </div>
          </el-card>
        </div>
      </el-card>

      <!-- Modal Dialog for Preference Request -->
      <el-dialog
        v-model="isModalVisible"
        title="提交时间偏好"
        width="500px"
        :close-on-click-modal="false"
        @close="closeRequestModal"
        destroy-on-close
      >
        <el-form :model="preferenceForm" ref="preferenceFormRef" label-width="90px" :rules="preferenceFormRules" @submit.prevent="handleSubmitPreference">
            <el-alert v-if="modalErrorMessage" :title="modalErrorMessage" type="error" show-icon style="margin-bottom: 15px;" @close="modalErrorMessage=''"/>

          <el-form-item label="选择学期:" prop="semester_id">
            <el-select v-model="preferenceForm.semester_id" placeholder="请选择学期" clearable filterable style="width: 100%;">
              <el-option
                v-for="semester in semesters"
                :key="semester.id"
                :label="semester.name"
                :value="semester.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="日期/节次:" prop="timeslot_id">
            <el-select v-model="preferenceForm.timeslot_id" placeholder="请选择日期和节次" clearable filterable style="width: 100%;">
               <el-option
                 v-for="ts in availableTimeSlots"
                 :key="ts.id"
                 :label="`${ts.day_of_week} 第 ${ts.period} 节 (${ts.start_time} - ${ts.end_time})`"
                 :value="ts.id"
               />
            </el-select>
          </el-form-item>

          <el-form-item label="偏好类型:" prop="preference_type">
            <el-select v-model="preferenceForm.preference_type" placeholder="请选择偏好类型" style="width: 100%;">
              <el-option label="避免安排 (不希望排课)" value="avoid" />
              <!-- <el-option label="优先安排 (希望排课)" value="prefer" /> -->
            </el-select>
          </el-form-item>

          <el-form-item label="原因:" prop="reason">
            <el-input
              type="textarea"
              v-model="preferenceForm.reason"
              :rows="3"
              placeholder="请详细描述您的原因 (可选)"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>
        </el-form>

        <template #footer>
          <span class="dialog-footer">
            <el-button @click="closeRequestModal" :disabled="isLoading">取消</el-button>
            <el-button type="primary" @click="handleSubmitPreference" :loading="isLoading">
              提交偏好
            </el-button>
          </span>
        </template>
      </el-dialog>

    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, nextTick } from 'vue';
import axios from 'axios';
import {
    ElCard, ElButton, ElDialog, ElForm, ElFormItem, ElSelect, ElOption,
    ElInput, ElTag, ElAlert, ElEmpty, ElLoading, ElMessage, ElMessageBox
} from 'element-plus';
import { Plus, Delete } from '@element-plus/icons-vue';

// --- Configuration ---
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// --- State ---
const isModalVisible = ref(false);
const isLoading = ref(false); // Loading state for submitting new preference (modal)
const isPreferencesLoading = ref(false); // Loading state for fetching preferences list
const preferencesError = ref(null); // Error message for fetching preferences list

const loggedInUserId = ref(null);
const semesters = ref([]);
const availableTimeSlots = ref([]);
const teacherPreferences = ref([]);

// --- Form Data & Validation ---
const preferenceFormRef = ref(null); // Ref for the el-form instance
const preferenceForm = reactive({ // Use reactive for the form object
    semester_id: null,
    timeslot_id: null,
    preference_type: 'avoid', // Default value
    reason: '',
});
const preferenceFormRules = reactive({
    semester_id: [{ required: true, message: '请选择学期', trigger: 'change' }],
    timeslot_id: [{ required: true, message: '请选择日期和节次', trigger: 'change' }],
    preference_type: [{ required: true, message: '请选择偏好类型', trigger: 'change' }],
    // Reason is optional
});
const modalErrorMessage = ref(''); // Specific error message inside the modal

// --- Delete State ---
const isDeleting = ref({}); // Use an object { [preferenceId]: boolean }


// --- Lifecycle Hooks ---
onMounted(async () => {
   const storedUserId = localStorage.getItem('user_id');
   const storedUserRole = localStorage.getItem('userRole');

   if (storedUserId && storedUserRole && storedUserRole.toLowerCase() === 'teacher') {
       loggedInUserId.value = Number(storedUserId);
       console.log(`Teacher Scheduling Request: User ID ${loggedInUserId.value} (Role: ${storedUserRole}) logged in.`);
       isPreferencesLoading.value = true; // Start loading indicator early
       await fetchInitialData(); // Fetch semesters, timeslots, and preferences
       isPreferencesLoading.value = false;
   } else {
       console.error('Teacher Scheduling Request: Invalid or missing user ID/role in localStorage.');
       preferencesError.value = '未能获取有效的教师登录信息，无法加载数据。请尝试重新登录。';
       // Optionally redirect to login
   }
});

// --- Methods ---

// Fetch initial data needed for the component
const fetchInitialData = async () => {
    try {
        await Promise.all([
            fetchSemesters(),
            fetchTimeSlots(),
            fetchTeacherPreferences(loggedInUserId.value)
        ]);
    } catch (error) {
        console.error("Error fetching initial data:", error);
        // Specific errors are handled in individual fetch functions,
        // but a general error could be shown here if needed.
        if (!preferencesError.value) { // Avoid overwriting specific error
            preferencesError.value = '加载页面基础数据时出错，请刷新页面或稍后再试。';
        }
    }
};

const fetchSemesters = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
  } catch (error) {
    console.error('Error fetching semesters:', error);
    ElMessage.error('无法加载学期信息。');
    throw error; // Re-throw to be caught by fetchInitialData if necessary
  }
};

const fetchTimeSlots = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/time-slots`);
    // Sort timeslots for better display in dropdown
    availableTimeSlots.value = response.data.sort((a, b) => {
        const dayOrder = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        const dayAIndex = dayOrder.indexOf(a.day_of_week);
        const dayBIndex = dayOrder.indexOf(b.day_of_week);
        if (dayAIndex !== dayBIndex) {
            return dayAIndex - dayBIndex;
        }
        return a.period - b.period;
    });
    console.log('Fetched and Sorted Time Slots:', availableTimeSlots.value);
  } catch (error) {
    console.error('Error fetching time slots:', error);
    ElMessage.error('无法加载时间段信息。');
     throw error;
  }
};

const fetchTeacherPreferences = async (userId) => {
    if (!userId) {
        preferencesError.value = '无法获取用户ID，无法加载偏好列表。';
        return;
    }
    // No need to set loading here if called from fetchInitialData which sets it
    // isPreferencesLoading.value = true;
    preferencesError.value = null;

    try {
        const response = await axios.get(`${API_BASE_URL}/api/teacher/${userId}/scheduling-preferences`);
        teacherPreferences.value = response.data;
        console.log('Fetched Teacher Preferences:', teacherPreferences.value);
        // Initialize isDeleting state for all preferences
        const deletingState = {};
        teacherPreferences.value.forEach(pref => {
            deletingState[pref.id] = false;
        });
        isDeleting.value = deletingState;

    } catch (error) {
        console.error('Error fetching teacher preferences:', error);
        if (error.response) {
            preferencesError.value = error.response.data.message || `加载偏好列表失败: ${error.response.statusText}`;
        } else {
            preferencesError.value = '加载偏好列表时发生网络错误或服务器无响应。';
        }
         throw error;
    } finally {
        // isPreferencesLoading.value = false; // Handled by caller fetchInitialData
    }
};


const openRequestModal = () => {
  if (loggedInUserId.value === null) {
      ElMessage.warning('请先登录教师账号再提出要求。');
      return;
  }
   if (semesters.value.length === 0 || availableTimeSlots.value.length === 0) {
       ElMessage.warning('学期或时间段信息尚未加载完成，请稍候再试。');
       return;
   }

  // Reset form data (important when using reactive)
  Object.assign(preferenceForm, {
      semester_id: null,
      timeslot_id: null,
      preference_type: 'avoid',
      reason: '',
  });
  modalErrorMessage.value = ''; // Clear previous modal errors
  isModalVisible.value = true;

  // Clear validation state after the dialog is opened and form rendered
  nextTick(() => {
      preferenceFormRef.value?.clearValidate();
  });
};

const closeRequestModal = () => {
  isModalVisible.value = false;
  // No need to explicitly reset form if using destroy-on-close in el-dialog
  // preferenceFormRef.value?.resetFields(); // Optional: Reset fields if needed without destroy-on-close
};

const handleSubmitPreference = async () => {
  if (!preferenceFormRef.value) return;
  if (loggedInUserId.value === null) {
       modalErrorMessage.value = '无法获取您的用户ID，请重新登录。';
       return;
  }

  await preferenceFormRef.value.validate(async (valid) => {
    if (valid) {
        isLoading.value = true;
        modalErrorMessage.value = '';

        const preferenceData = {
            user_id: loggedInUserId.value,
            semester_id: preferenceForm.semester_id,
            timeslot_id: preferenceForm.timeslot_id,
            preference_type: preferenceForm.preference_type.toLowerCase(),
            reason: preferenceForm.reason,
        };

        console.log('提交教师时间偏好:', preferenceData);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/teacher/scheduling-preferences`, preferenceData);
            ElMessage.success(response.data.message || '时间偏好已提交成功！');
            closeRequestModal();
            await fetchTeacherPreferences(loggedInUserId.value); // Refresh list
        } catch (error) {
            console.error('Submit preference error:', error);
            if (error.response) {
                 let errMsg = error.response.data.error || error.response.data.message || `提交偏好失败: ${error.response.statusText}`;
                 if (error.response.status === 400 && error.response.data.message && error.response.data.message.includes("数据完整性错误")) {
                     errMsg += " (您可能已为该学期该时段提交过同类偏好)";
                 }
                  modalErrorMessage.value = errMsg;
            } else {
                modalErrorMessage.value = '提交偏好时发生网络错误或服务器无响应。';
            }
        } finally {
            isLoading.value = false;
        }
    } else {
        console.log('表单验证失败');
        modalErrorMessage.value = '请检查表单输入项。';
        return false;
    }
  });
};

// --- Delete Functions ---
const confirmDeletePreference = async (preferenceId) => {
     if (loggedInUserId.value === null) {
       ElMessage.error('无法获取您的用户ID，请重新登录。');
       return;
    }
    try {
        await ElMessageBox.confirm(
            '确定要删除此排课时间偏好吗？此操作不可恢复。',
            '确认删除',
            {
                confirmButtonText: '确定删除',
                cancelButtonText: '取消',
                type: 'warning',
            }
        );
        // User confirmed
        await deletePreference(preferenceId);
    } catch (action) {
        // User clicked cancel or closed the box
        if (action === 'cancel') {
            ElMessage.info('已取消删除');
        }
    }
}

const deletePreference = async (preferenceId) => {
    isDeleting.value = { ...isDeleting.value, [preferenceId]: true }; // Set loading state

    console.log('尝试删除偏好:', preferenceId);

    try {
        // IMPORTANT: Pass user_id securely for backend verification.
        // Example uses query param (LESS SECURE). Use token/session or headers in production.
        const response = await axios.delete(`${API_BASE_URL}/api/teacher/scheduling-preferences/${preferenceId}`, {
            // Option 1: Query Param (Less Secure)
            params: { user_id: loggedInUserId.value }
            // Option 2: Header (If backend expects it)
            // headers: { 'X-User-ID': loggedInUserId.value }
        });

        ElMessage.success(response.data.message || '偏好删除成功！');

        // Remove the deleted item from the list directly for faster UI update
        teacherPreferences.value = teacherPreferences.value.filter(pref => pref.id !== preferenceId);

    } catch (error) {
        console.error('Delete preference error:', error);
        if (error.response) {
            ElMessage.error(error.response.data.error || error.response.data.message || `删除偏好失败: ${error.response.statusText}`);
        } else {
            ElMessage.error('删除偏好时发生网络错误或服务器无响应。');
        }
    } finally {
        isDeleting.value = { ...isDeleting.value, [preferenceId]: false }; // Reset loading state
    }
};
// --- End Delete Functions ---

// --- Helper Functions for Display ---
const getPreferenceTypeTag = (type) => {
    // Map preference type to Element Plus tag types
    switch (type?.toLowerCase()) {
        case 'avoid': return 'danger';
        case 'prefer': return 'success';
        default: return 'info';
    }
};

const getStatusTagType = (status) => {
    // Map status to Element Plus tag types
     switch (status?.toLowerCase()) {
        case 'pending': return 'warning';
        case 'approved': return 'success';
        case 'rejected': return 'danger';
        case 'applied': return 'info'; // Or maybe 'primary'
        default: return 'info';
    }
}

</script>

<style scoped>
.page-content {
  padding: 20px;
  max-width: 900px; /* Slightly wider */
  margin: 0 auto;
}

.main-card {
    border: none; /* Remove border from main card if sections have borders */
}

.card-header {
  font-size: 2em;
  font-weight: bold;
}

.section-card {
  margin-top: 20px;
}
.section-card h3 {
    margin: 0; /* Remove default margin from h3 inside card header */
    font-size: 1.1em;
}

.preferences-list {
    margin-top: 15px;
}

.preference-item {
    margin-bottom: 15px;
    border: 1px solid #e4e7ed; /* Lighter border for inner cards */
    display: flex; /* Use flex for main layout */
    justify-content: space-between; /* Push actions to the right */
    align-items: flex-start; /* Align items to the top */
}
.el-card__body { /* Reduce padding inside preference item cards */
    padding: 15px;
    width: 100%; /* Ensure body takes full width within flex */
}
.preference-content {
    flex-grow: 1; /* Allow content to take available space */
    margin-right: 15px; /* Space between content and actions */
}
.preference-main-info {
    font-size: 1.05em;
    color: #303133;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    flex-wrap: wrap; /* Allow info to wrap on smaller screens */
}

.semester-name {
    font-weight: bold;
    margin-right: 10px;
    color: #409EFF; /* Element Plus primary color */
}

.timeslot-info {
    margin-right: 10px;
    color: #606266;
}

.preference-status-time {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.9em;
    color: #909399;
    margin-bottom: 8px;
    flex-wrap: wrap;
}
.preference-status {
    margin-right: 15px; /* Space between status and timestamp */
}

.preference-reason {
    font-size: 0.9em;
    color: #606266;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed #dcdfe6;
}
.preference-reason span {
    font-style: italic;
    color: #555;
}

.preference-actions {
    flex-shrink: 0; /* Prevent actions button from shrinking */
}

.dialog-footer {
    text-align: right;
}

/* Adjust el-select dropdown width if needed */
/* .el-select-dropdown { max-width: 400px; } */
</style>
