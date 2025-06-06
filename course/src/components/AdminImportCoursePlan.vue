<template>
  <div class="course-plan-management">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>课程计划管理</span>
        </div>
      </template>

      <!-- Header Controls -->
      <div class="header-controls">
        <el-form :inline="true" class="control-form">
          <el-form-item label="选择学期:" class="semester-selector-item">
            <el-select
              v-model="selectedSemesterId"
              placeholder="请选择学期"
              @change="handleSemesterChange"
              clearable
              filterable
              style="width: 250px;"
            >
              <el-option
                v-for="semester in semesters"
                :key="semester.id"
                :label="semester.name"
                :value="semester.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item>
             <el-button
               type="primary"
               @click="handleManualAdd"
               :disabled="!selectedSemesterId"
               :icon="Plus"
               style="margin-left: 200px;"
             >
               手动添加
             </el-button>
             <el-button @click="handleDownloadTemplate" :icon="Download" style="margin-left: 20px;">
               下载模板
             </el-button>
             <input type="file" ref="fileInputRef" style="display: none;" @change="handleFileSelected" accept=".xls,.xlsx" />
             <el-button
               type="success"
               @click="triggerFileInput"
               :disabled="!selectedSemesterId || uploadStatus === 'uploading'"
               :loading="uploadStatus === 'uploading'"
               :icon="Upload"
                 style="margin-left: 20px;"
             >
               {{ uploadStatus === 'uploading' ? '上传中...' : '从Excel导入' }}
             </el-button>
             <el-button
               type="warning"
               @click="triggerScheduling"
               :disabled="!selectedSemesterId || schedulingStatus === 'running'"
               :loading="schedulingStatus === 'running'"
               :icon="Clock"
               style="margin-left: 20px;"
             >
               {{ schedulingStatus === 'running' ? '排课中...' : '开始排课' }}
             </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- Status Messages & Hints -->
      <el-alert v-if="uploadStatus === 'uploading'" title="正在导入Excel文件，请稍候..." type="info" :closable="false" show-icon class="status-alert"/>
      <el-alert v-if="successMessage" :title="successMessage" type="success" show-icon @close="successMessage=''" class="status-alert"/>
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage=''" class="status-alert"/>
      <el-alert v-if="schedulingMessage && schedulingStatus !== 'running'"
           :title="schedulingMessage"
           :type="getSchedulingAlertType()"
           show-icon
           @close="schedulingMessage=''"
           class="status-alert"/>


      <el-alert v-if="selectedSemesterId && !loading && coursePlans.length > 0" type="warning" show-icon :closable="false" class="status-alert">
          <template #title>
              提示: 从Excel导入将 <strong style="color: red;">覆盖</strong> 当前选定学期的所有课程计划。
              Excel文件应包含列：'学期名称', '专业名称', '课程名称', '总课时', '课程类型', '授课教师姓名', '是否核心课程', '预计学生人数'。
          </template>
      </el-alert>

      <!-- Table Area -->
      <div v-if="selectedSemesterId">
          <el-table
            :data="coursePlans"
            stripe
            border
            v-loading="loading"
            style="width: 100%; margin-top: 20px;"
            empty-text="当前学期没有课程计划数据"
          >
            <el-table-column prop="major_name" label="专业" width="200" align="center" />
            <el-table-column prop="course_name" label="课程名称" width="200" align="center" />
            <el-table-column prop="course_type" label="课程类型" width="120"  align="center"/>
            <el-table-column prop="total_sessions" label="总学时" width="120" align="center" />
            <el-table-column prop="teacher_name" label="授课教师" width="120" align="center" />
            <el-table-column prop="is_core_course" label="核心课" width="100" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.is_core_course ? 'success' : 'info'" disable-transitions>
                  {{ scope.row.is_core_course ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="expected_students" label="预计人数" width="100" align="center" />
            <el-table-column label="操作" width="220" fixed="right" align="center">
              <template #default="scope">
                <el-button
                  type="primary"
                  link
                  size="large"
                  :icon="Edit"
                  @click="handleEditCourse(scope.row)"
                >编辑</el-button>
                <el-button
                  type="danger"
                  link
                  size="large"
                  :icon="Delete"
                  @click="handleDeleteCourse(scope.row.id, scope.row.course_name)"
                >删除</el-button>
              </template>
            </el-table-column>
          </el-table>
      </div>
      <el-empty v-else description="请先选择一个学期以查看或管理课程计划" />

    </el-card>

    <!-- Modal Dialog for Add/Edit Course Plan -->
    <el-dialog
      v-model="isModalOpen"
      :title="modalMode === 'add' ? '添加新课程计划' : '编辑课程计划'"
      width="60%"
      :close-on-click-modal="false"
      @close="closeModal"
      top="5vh"
      destroy-on-close
    >
      <el-form :model="currentPlan" ref="planFormRef" label-width="120px" :rules="planFormRules" v-loading="isFetchingDropdownData">
         <el-alert v-if="modalErrorMessage" :title="modalErrorMessage" type="error" show-icon @close="modalErrorMessage=''" style="margin-bottom: 15px;"/>

         <el-row :gutter="20">
            <el-col :span="12">
               <el-form-item label="专业:" prop="major_id">
                 <el-select v-model="currentPlan.major_id" placeholder="请选择专业" filterable clearable style="width: 100%;">
                   <el-option
                     v-for="major in majorsList"
                     :key="major.id"
                     :label="major.name"
                     :value="major.id"
                   />
                 </el-select>
               </el-form-item>
            </el-col>
            <el-col :span="12">
               <el-form-item label="授课教师:" prop="teacher_id">
                 <el-select v-model="currentPlan.teacher_id" placeholder="请选择教师" filterable clearable style="width: 100%;">
                   <el-option
                     v-for="teacher in teachersList"
                     :key="teacher.id"
                     :label="teacher.name"
                     :value="teacher.id"
                   />
                 </el-select>
               </el-form-item>
            </el-col>
         </el-row>

          <el-row :gutter="20">
            <el-col :span="12">
                <el-form-item label="课程名称:" prop="course_name">
                  <el-input v-model.trim="currentPlan.course_name" placeholder="请输入课程名称" clearable />
                </el-form-item>
            </el-col>
             <el-col :span="12">
                <el-form-item label="课程类型:" prop="course_type">
                  <el-input v-model.trim="currentPlan.course_type" placeholder="例如: 理论课, 实验课" clearable />
                </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="总课时:" prop="total_sessions">
                  <el-input-number v-model="currentPlan.total_sessions" :min="0" controls-position="right" style="width: 100%;"/>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="预计学生人数:" prop="expected_students">
                  <el-input-number v-model="currentPlan.expected_students" :min="0" controls-position="right" style="width: 100%;"/>
                </el-form-item>
              </el-col>
          </el-row>

          <el-form-item label="核心课程:" prop="is_core_course">
            <el-checkbox v-model="currentPlan.is_core_course" label="是否核心课程" size="large"/>
          </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeModal" :disabled="isSubmittingModal">取消</el-button>
          <el-button
            type="primary"
            @click="handleSubmitPlan"
            :loading="isSubmittingModal"
          >
            {{ isSubmittingModal ? '提交中...' : (modalMode === 'add' ? '添加计划' : '保存更改') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, reactive } from 'vue';
import axios from 'axios';
// Import Element Plus components and utilities
import {
    ElCard, ElForm, ElFormItem, ElSelect, ElOption, ElButton, ElInput, ElUpload, // ElUpload if using it
    ElTable, ElTableColumn, ElTag, ElDialog, ElCheckbox, ElInputNumber, ElAlert, ElEmpty, ElRow, ElCol,
    ElMessage, ElMessageBox, ElLoading
} from 'element-plus';
// Import Element Plus icons (make sure you've installed @element-plus/icons-vue)
import { Plus, Download, Upload, Clock, Edit, Delete } from '@element-plus/icons-vue';

// --- Configuration ---
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// --- State ---
const semesters = ref([]);
const selectedSemesterId = ref(null); // Use null for clearer initial state with el-select clearable
const coursePlans = ref([]);
const fileInputRef = ref(null);

// --- Status Flags ---
const loading = ref(false); // Combined loading status for main data
const errorMessage = ref('');
const successMessage = ref('');
const uploadStatus = ref(''); // 'uploading', 'success', 'error', ''
const schedulingStatus = ref(''); // '', 'running', 'success', 'error', 'success_no_tasks'
const schedulingMessage = ref('');

// --- Modal State ---
const isModalOpen = ref(false);
const modalMode = ref('add'); // 'add' or 'edit'
const planFormRef = ref(null); // Ref for the el-form instance
const currentPlan = reactive({ // Use reactive for nested object changes
  id: null, // Keep track of ID for editing
  semester_id: null,
  major_id: null,
  course_name: '',
  total_sessions: null,
  course_type: '理论课',
  teacher_id: null,
  is_core_course: false,
  expected_students: null,
});
// const editingPlanId = ref(null); // No longer needed if ID is in currentPlan
const majorsList = ref([]);
const teachersList = ref([]);
const modalErrorMessage = ref('');
const isSubmittingModal = ref(false);
const isFetchingDropdownData = ref(false); // Loading state for dropdowns in modal

// --- Form Validation Rules ---
const planFormRules = reactive({
  major_id: [{ required: true, message: '请选择专业', trigger: 'change' }],
  teacher_id: [{ required: true, message: '请选择授课教师', trigger: 'change' }],
  course_name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  total_sessions: [
    { required: true, message: '请输入总课时', trigger: 'blur' },
    { type: 'number', message: '总课时必须是数字', trigger: ['blur', 'change']},
    { validator: (rule, value, callback) => value >= 0 ? callback() : callback(new Error('总课时不能为负数')), trigger: 'blur'}
  ],
  expected_students: [
    { required: true, message: '请输入预计学生人数', trigger: 'blur' },
    { type: 'number', message: '预计人数必须是数字', trigger: ['blur', 'change']},
    { validator: (rule, value, callback) => value >= 0 ? callback() : callback(new Error('预计人数不能为负数')), trigger: 'blur'}
  ],
  // course_type is not strictly required based on original code
});


// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchSemesters();
  // Lazy load dropdown data when modal opens for the first time
  // await fetchModalDropdownData(); // Or load here if preferred
});

// Watcher for semester change
watch(selectedSemesterId, (newVal) => {
  handleSemesterChange(newVal); // Call handler function
});


// --- Methods ---

const clearMainMessages = () => {
    errorMessage.value = '';
    successMessage.value = '';
    schedulingMessage.value = '';
    // uploadStatus is handled separately
};

const handleSemesterChange = (semesterId) => {
    clearMainMessages();
    coursePlans.value = []; // Clear plans immediately
    if (semesterId) {
        fetchCoursePlans(); // Auto-fetch when semester changes and is valid
    }
};


const fetchSemesters = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
  } catch (error) {
    console.error('获取学期列表失败:', error);
    ElMessage.error(`获取学期列表失败: ${error.response?.data?.message || error.message}`);
  } finally {
    loading.value = false;
  }
};

const fetchCoursePlans = async () => {
  if (!selectedSemesterId.value) {
    coursePlans.value = [];
    return;
  }
  loading.value = true;
  clearMainMessages();
  try {
    const response = await axios.get(`${API_BASE_URL}/api/course-plans`, {
      params: { semester_id: selectedSemesterId.value }
    });
    coursePlans.value = response.data;
  } catch (error) {
    console.error('获取课程计划失败:', error);
    coursePlans.value = []; // Clear on error
    errorMessage.value = `获取课程计划失败: ${error.response?.data?.message || error.message}`;
    // ElMessage.error(`获取课程计划失败: ${error.response?.data?.message || error.message}`); // Use alert or message
  } finally {
    loading.value = false;
  }
};

const triggerFileInput = () => {
  clearMainMessages();
  uploadStatus.value = ''; // Reset upload status
  fileInputRef.value.click();
};

const handleFileSelected = (event) => {
  const file = event.target.files[0];
  if (file) {
    handleImportExcel(file);
  }
  // Reset file input value so @change triggers again for the same file
  if (fileInputRef.value) {
      fileInputRef.value.value = '';
  }
};

const handleImportExcel = async (file) => {
  if (!selectedSemesterId.value) {
    ElMessage.warning('请先选择一个学期才能导入课程计划。');
    return;
  }
  clearMainMessages();
  uploadStatus.value = 'uploading';

  const formData = new FormData();
  formData.append('file', file);
  formData.append('semester_id', selectedSemesterId.value);

  try {
    const response = await axios.post(`${API_BASE_URL}/api/course-plans/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    successMessage.value = response.data.message || 'Excel文件导入成功！';
    // ElMessage.success(response.data.message || 'Excel文件导入成功！'); // Alternative
    uploadStatus.value = 'success';
    await fetchCoursePlans(); // Refresh list
  } catch (error) {
    console.error('Excel导入失败:', error);
    errorMessage.value = `Excel导入失败: ${error.response?.data?.message || '未知错误，请检查文件格式或联系管理员。'}`;
    // ElMessage.error(`Excel导入失败: ${error.response?.data?.message || '未知错误'}`); // Alternative
    uploadStatus.value = 'error';
  } finally {
     // Reset status only if it was uploading, might have finished with success/error
     if (uploadStatus.value === 'uploading') uploadStatus.value = '';
  }
};

const handleDownloadTemplate = async () => {
  clearMainMessages();
  const loadingInstance = ElLoading.service({ text: '正在准备模板下载...' });
  try {
    const response = await axios.get(`${API_BASE_URL}/api/course-plans/template`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const contentDisposition = response.headers['content-disposition'];
    let fileName = 'course_plan_template.xlsx';
    if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (fileNameMatch && fileNameMatch.length === 2) fileName = decodeURIComponent(fileNameMatch[1]); // Decode filename
    }
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    ElMessage.success('课程计划模板已开始下载。');
  } catch (error) {
    console.error('下载模板失败:', error);
    ElMessage.error(`下载模板失败: ${error.response?.data?.message || error.message}`);
  } finally {
      loadingInstance.close();
  }
};

const handleDeleteCourse = async (planId, courseName) => {
    try {
        await ElMessageBox.confirm(
            `确定要删除课程计划 “${courseName}” (ID: ${planId}) 吗？此操作不可恢复。`,
            '确认删除',
            {
                confirmButtonText: '确定删除',
                cancelButtonText: '取消',
                type: 'warning',
            }
        );
        // User confirmed
        clearMainMessages();
        loading.value = true; // Indicate loading during delete
        try {
            await axios.delete(`${API_BASE_URL}/api/course-plans/${planId}`);
            ElMessage.success(`课程计划 “${courseName}” 已成功删除！`);
            await fetchCoursePlans(); // Refresh list
        } catch (error) {
            console.error(`删除课程计划 ${planId} 失败:`, error);
            ElMessage.error(`删除失败: ${error.response?.data?.message || error.message}`);
        } finally {
            loading.value = false;
        }
    } catch (action) {
        // User clicked cancel or closed the box
        if (action === 'cancel') {
            ElMessage.info('已取消删除');
        }
    }
};


const fetchModalDropdownData = async () => {
    if (majorsList.value.length > 0 && teachersList.value.length > 0) return; // Already loaded

    isFetchingDropdownData.value = true;
    modalErrorMessage.value = '';
    try {
        const [majorsRes, teachersRes] = await Promise.all([
            axios.get(`${API_BASE_URL}/api/majors-list`),
            axios.get(`${API_BASE_URL}/api/teachers-list`)
        ]);
        majorsList.value = majorsRes.data;
        teachersList.value = teachersRes.data;
    } catch (error) {
        console.error('加载专业/教师列表失败:', error);
        modalErrorMessage.value = '加载下拉选项失败，请稍后重试。';
        // Close modal if critical data failed? Or disable form fields?
    } finally {
        isFetchingDropdownData.value = false;
    }
};

const openModal = async (mode, plan = null) => {
  modalMode.value = mode;
  modalErrorMessage.value = '';

  // Ensure dropdown data is available, fetch if needed
  await fetchModalDropdownData();
  if (isFetchingDropdownData.value) { // Still fetching? Wait maybe? Or disable form?
       console.warn("Dropdown data still fetching, modal opened.");
       // Could show a loading indicator inside the form instead
  }
  if (modalErrorMessage.value) { // If fetch failed
       ElMessage.error('无法加载表单所需数据，请稍后再试。');
       return; // Don't open modal if critical data missing
  }


  if (mode === 'add') {
    // Reset reactive object fields
    Object.assign(currentPlan, {
      id: null,
      semester_id: selectedSemesterId.value, // Auto-set current semester
      major_id: null,
      course_name: '',
      total_sessions: null,
      course_type: '理论课',
      teacher_id: null,
      is_core_course: false,
      expected_students: null,
    });
    // editingPlanId.value = null; // Not needed if ID is in currentPlan
  } else if (mode === 'edit' && plan) {
    // Assign values from the selected plan
     Object.assign(currentPlan, {
      id: plan.id, // This is course_assignments.id
      semester_id: plan.semester_id,
      major_id: plan.major_id,
      teacher_id: plan.teacher_id,
      course_name: plan.course_name,
      total_sessions: plan.total_sessions,
      course_type: plan.course_type,
      is_core_course: plan.is_core_course,
      expected_students: plan.expected_students,
    });
    // editingPlanId.value = plan.id; // Not needed
  }
  isModalOpen.value = true;
  // Reset validation state after modal opens and form is rendered
  await nextTick(); // Wait for DOM update
  if (planFormRef.value) {
      planFormRef.value.clearValidate();
  }
};

const closeModal = () => {
  isModalOpen.value = false;
  if (planFormRef.value) {
    planFormRef.value.resetFields(); // Resets to initial values (might require prop setting in el-form-item) or clearValidate()
  }
   // Explicitly reset reactive object to default state if resetFields is not enough
    Object.assign(currentPlan, { id: null, semester_id: null, major_id: null, course_name: '', total_sessions: null, course_type: '理论课', teacher_id: null, is_core_course: false, expected_students: null, });
    modalErrorMessage.value = '';
};

const handleManualAdd = () => {
  if (!selectedSemesterId.value) {
    ElMessage.warning('请先选择一个学期才能添加课程计划。');
    return;
  }
  openModal('add');
};

const handleEditCourse = (plan) => {
  openModal('edit', plan);
};

const handleSubmitPlan = async () => {
  if (!planFormRef.value) return;

  await planFormRef.value.validate(async (valid) => {
    if (valid) {
      modalErrorMessage.value = '';
      isSubmittingModal.value = true;

      const payload = { ...currentPlan }; // Get current values from reactive object
       // Ensure semester_id is set correctly, especially for 'add' mode
      if (modalMode.value === 'add' && !payload.semester_id) {
          payload.semester_id = selectedSemesterId.value;
      }

       if (!payload.semester_id) { // Final check
           modalErrorMessage.value = '未指定学期，无法提交。';
           isSubmittingModal.value = false;
           return;
       }


      try {
        clearMainMessages(); // Clear main page messages before new action
        if (modalMode.value === 'add') {
          // No ID in payload for POST
          const { id, ...addPayload } = payload;
          await axios.post(`${API_BASE_URL}/api/course-plans`, addPayload);
          ElMessage.success('新课程计划添加成功！');
        } else { // 'edit'
          // Send PUT request with ID in URL, payload contains updated data
          await axios.put(`${API_BASE_URL}/api/course-plans/${payload.id}`, payload);
          ElMessage.success(`课程计划 (ID: ${payload.id}) 更新成功！`);
        }
        closeModal();
        await fetchCoursePlans(); // Refresh the list
      } catch (error) {
        console.error('保存课程计划失败:', error);
        modalErrorMessage.value = `保存失败: ${error.response?.data?.message || error.message}`;
      } finally {
        isSubmittingModal.value = false;
      }
    } else {
      console.log('表单验证失败');
      modalErrorMessage.value = '请检查表单输入项。';
      return false;
    }
  });
};

const triggerScheduling = async () => {
  if (!selectedSemesterId.value) {
    ElMessage.warning('请先选择一个学期以进行排课。');
    return;
  }
  try {
      const semesterName = semesters.value.find(s=>s.id === selectedSemesterId.value)?.name || `ID: ${selectedSemesterId.value}`;
      await ElMessageBox.confirm(
          `确定要为选定学期【${semesterName}】开始自动排课吗？<br/><strong>这将清空该学期现有排课结果并重新生成。</strong>`,
          '确认排课',
          {
              confirmButtonText: '开始排课',
              cancelButtonText: '取消',
              type: 'warning',
              dangerouslyUseHTMLString: true, // Allow <br> and <strong>
          }
      );
      // User confirmed
      schedulingStatus.value = 'running';
      schedulingMessage.value = '';
      clearMainMessages(); // Clear other messages
      errorMessage.value = ''; // Specifically clear error message
      successMessage.value = ''; // Specifically clear success message

      const loadingInstance = ElLoading.service({
          lock: true,
          text: '正在执行排课，请稍候...',
          background: 'rgba(0, 0, 0, 0.7)',
      });

      try {
          const response = await axios.post(`${API_BASE_URL}/api/schedule/run/${selectedSemesterId.value}`);
          schedulingStatus.value = 'success'; // Assume success unless response indicates otherwise

          let summaryText = `排课完成：${response.data.message}\n`;
           // Check response.data.summary and format message...
          if (response.data.summary && typeof response.data.summary === 'object') {
              const summary = response.data.summary;
              // Example: Append details if available
              // if (summary.assignments_processed) summaryText += `处理计划数: ${summary.assignments_processed}\n`;
              // if (summary.entries_created) summaryText += `生成条目数: ${summary.entries_created}\n`;
              if (summary.errors && summary.errors.length > 0) {
                 summaryText += "\n错误/警告详情:\n" + summary.errors.join("\n");
                 // Determine overall status based on errors
                 if (response.data.message.includes("部分")) { // Example check
                     schedulingStatus.value = 'warning'; // Or keep 'success' if it's just warnings
                 } else {
                    // Maybe still 'success' if backend considers it successful despite warnings
                 }
              } else if(response.data.message.includes("没有需要排课")) {
                  schedulingStatus.value = 'success_no_tasks';
              }
          } else {
              summaryText += "未能获取详细排课统计信息。\n";
              console.warn("Backend did not return a valid summary object:", response.data.summary);
              if (response.data.message.includes("没有需要排课")) {
                  schedulingStatus.value = 'success_no_tasks';
              }
          }
          schedulingMessage.value = summaryText;
          // Decide if you want this in successMessage too or just the specific scheduling alert
          // successMessage.value = summaryText;

      } catch (error) {
          console.error('排课执行失败:', error);
          schedulingStatus.value = 'error';
          const errorMsgText = error.response?.data?.message || error.message || '未知错误';
          schedulingMessage.value = `排课失败: ${errorMsgText}`;
      } finally {
          loadingInstance.close();
           // Don't reset running status here, let the success/error state persist
           // if (schedulingStatus.value === 'running') schedulingStatus.value = '';
      }
  } catch (action) {
        if (action === 'cancel') {
            ElMessage.info('已取消排课');
        }
  }
};

// Helper to determine alert type for scheduling message
const getSchedulingAlertType = () => {
    switch (schedulingStatus.value) {
        case 'success': return 'success';
        case 'success_no_tasks': return 'info';
        case 'error': return 'error';
        case 'warning': return 'warning'; // If you add a warning status
        default: return 'info';
    }
};

</script>

<style scoped>
.course-plan-management {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 2.0em;
  font-weight: bold;
}
.header-controls {
  margin-bottom: 15px;
  /* display: flex; Should be handled by el-form inline */
  /* justify-content: space-between; */
  /* align-items: center; */
}
.control-form .el-form-item {
    margin-bottom: 10px; /* Adjust spacing for inline form */
    margin-right: 15px;
}
.semester-selector-item {
    margin-right: 30px !important; /* Add more space after semester selector */
}

.status-alert {
    margin-bottom: 15px;
}

/* Reduce default padding in table cells for denser view */
.el-table th.el-table__cell, .el-table td.el-table__cell {
    padding: 8px 10px;
}

.dialog-footer {
    text-align: right;
}

/* Style for the checkbox label */
.el-form-item__content .el-checkbox {
    line-height: normal; /* Adjust if needed */
}
.el-form-item__content .el-checkbox__label {
    padding-left: 8px;
}


</style>
