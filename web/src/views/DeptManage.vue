<template>
  <div class="page">
    <!-- 1. 顶部按钮 -->
    <el-button type="primary" @click="handleCreate">
      <el-icon style="margin-right: 4px"><Plus /></el-icon>
      创建部门
    </el-button>

    <!-- 2. 部门列表 -->
    <el-table :data="depts" style="margin-top: 20px" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="部门名称" />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="handleEdit(row)">修改</el-button>
          <el-button size="small" type="success" @click="handleAssign(row)">分配</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 3. 添加/编辑 弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '修改部门' : '创建部门'" 
      width="400px"
      @close="resetForm"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入部门名称" autofocus />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 4. 分配账号 弹窗 (新增功能) -->
    <el-dialog 
      v-model="assignDialogVisible" 
      :title="`分配账号 - ${currentDeptName}`" 
      width="500px"
    >
      <el-alert 
        title="请勾选需要分配给该部门的账号" 
        type="info" 
        :closable="false" 
        style="margin-bottom: 15px"
      />
      
      <!-- 模拟账号列表 -->
      <el-checkbox-group v-model="selectedUserIds" style="display: flex; flex-direction: column; gap: 10px;">
        <el-checkbox 
          v-for="user in allUsers" 
          :key="user.id" 
          :value="user.id"
          border
        >
          {{ user.username }} ({{ user.email }})
        </el-checkbox>
      </el-checkbox-group>

      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAssign" :loading="submitLoading">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive,onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// --- 状态定义 ---
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false) // 控制增删改弹窗
const assignDialogVisible = ref(false) // 控制分配弹窗
const isEdit = ref(false)
const formRef = ref(null)
const currentDeptName = ref('') // 当前正在分配的部门名称
const selectedUserIds = ref([]) // 选中的用户ID列表

// 表单数据
const form = reactive({
  id: null,
  name: ''
})

// 验证规则
const rules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }]
}

// 模拟部门数据
const depts = ref([
  { id: 1, name: '技术部' },
  { id: 2, name: '产品部' }
])

// 账号数据
const allUsers = ref([])

// --- 生命周期 ---
onMounted(() => {
  fetchDepts()
})


// --- 基础功能方法 ---


// 获取部门列表
const fetchDepts = async()=>{
  depts.value = []
  loading.value = true
  try{
    const response = await fetch('http://localhost:8000/dept/list', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
      })
      if (!response.ok) {
        throw new Error('网络响应错误: ' + response.status);
      }
      const res = await response.json()
      for(const d of res.data) {
        depts.value.push({id: d.id, name: d.name})
      }
  }catch(error){
    ElMessage.error('获取列表失败')
  }finally{
    loading.value = false
  }
}

const handleCreate = () => {
  isEdit.value = false
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.id = row.id
  form.name = row.name
  dialogVisible.value = true
}

const submitForm = () => {
  if (!formRef.value) return
  formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true

      if(isEdit.value){
        try{
          const response = await fetch('http://localhost:8000/dept/update', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
              },
              body:JSON.stringify({id:form.id,name:form.name})
            })
            if (!response.ok) {
              console.log(response)
              throw new Error(response.status);
            }
            const res = await response.json()
            if (res.status === 'success') {
              //depts.value.push({ id: res.data.id, name: res.data.name })
              const index = depts.value.findIndex(item => item.id === form.id)
              if (index !== -1) depts.value[index].name = form.name
              ElMessage.success('修改成功。')
            }else if(res.status === 'error'){
              ElMessage.error(res.message)
            }
        }catch(error){
          console.log(error)
          ElMessage.error(error)
        }
      }else{
        try{
          const response = await fetch('http://localhost:8000/dept/create', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
              },
              body:JSON.stringify({name:form.name})
            })
            if (!response.ok) {
              console.log(response)
              throw new Error(response.status);
            }
            const res = await response.json()
            if (res.status === 'success') {
              depts.value.push({ id: res.data.id, name: res.data.name })
              ElMessage.success('创建成功')
            }else if(res.status === 'error'){
              ElMessage.error(res.message)
            }
        }catch(error){
          console.log(error)
          ElMessage.error(error)
        }
      }
      submitLoading.value = false
      dialogVisible.value = false
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除部门 "${row.name}" 吗？`, '警告', { type: 'warning' })
    .then(async () => {
      const index = depts.value.findIndex(item => item.id === row.id)
      if (index !== -1) {
        try{
          const response = await fetch('http://localhost:8000/dept/delete?id='+row.id, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
              },
            })
            if (!response.ok) {
              console.log(response)
              throw new Error(response.status);
            }
            const res = await response.json()
            if (res.status === 'success') {
              depts.value.splice(index, 1)
              ElMessage.success('删除成功')
            }else if(res.status === 'error'){
              ElMessage.error(res.message)
            }
        }catch(error){
          console.log(error)
          ElMessage.error(error)
        }
      }
    })
    .catch(() => {})
}

const resetForm = () => {
  if (formRef.value) formRef.value.resetFields()
  form.id = null
}

// --- 分配功能方法 (新增) ---

// 1. 点击分配按钮
const handleAssign = async (row) => {
  currentDeptName.value = row.name
  assignDialogVisible.value = true
  selectedUserIds.value = [] // 每次打开重置选中状态
  // 如果有后端数据，这里可以查询该部门已关联的用户ID并赋值给 selectedUserIds.value
  try{
    const response = await fetch('http://localhost:8000/dept/user?id='+row.id, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
      })
      if (!response.ok) {
        console.log(response)
        throw new Error(response.status);
      }
      const res = await response.json()
      if (res.status === 'success') {
        allUsers.value = res.data
        for(const d of res.data) {
          if(d.assign === 'Y') {
            selectedUserIds.value.push(d.id)
          }
        }
      }else if(res.status === 'error'){
        ElMessage.error(res.message)
      }
  }catch(error){
    console.log(error)
    ElMessage.error(error)
  }  
}

// 2. 提交分配
const submitAssign = async () => {
  submitLoading.value = true
  
  // 模拟 API 提交：部门ID 和 选中的用户ID数组
  const payload = {
    deptId: depts.value.find(d => d.name === currentDeptName.value)?.id,
    userIds: selectedUserIds.value
  }
  try{
    const response = await fetch('http://localhost:8000/dept/assign', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
        body:JSON.stringify(payload)
      })
      if (!response.ok) {
        console.log(response)
        throw new Error(response.status);
      }
      const res = await response.json()
      if (res.status === 'success') {
        ElMessage.success(res.message)
      }else if(res.status === 'error'){
        ElMessage.error(res.message)
      }
  }catch(error){
    console.log(error)
    ElMessage.error(error)
  }
  submitLoading.value = false
  assignDialogVisible.value = false
}
</script>

<style scoped>
.page {
  padding: 20px;
  background-color: #fff;
  border-radius: 4px;
}
</style>