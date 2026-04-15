<template>
  <div class="page">
    <!-- 1. 顶部操作栏 -->
    <div class="header">
      <el-button type="primary" @click="handleCreate">
        <el-icon style="margin-right: 4px"><Plus /></el-icon>
        创建账号
      </el-button>
    </div>

    <!-- 2. 用户列表表格 -->
    <el-table :data="users" style="margin-top: 20px" border stripe v-loading="loading">
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">{{ row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.active ? 'success' : 'info'">{{ row.active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="handleEdit(row)">修改</el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="handleDelete(row)" 
            :disabled="row.username === currentUser"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 3. 创建/修改 弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '修改账号信息' : '创建新账号'" 
      width="500px"
      @close="resetForm"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            :placeholder="isEdit ? '留空则不修改密码' : '请输入密码'" 
            show-password
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态" prop="active">
          <el-switch v-model="form.active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// --- 模拟数据与状态 ---
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false) // 标记当前是编辑模式还是创建模式
const formRef = ref(null)
const currentUser = ref('admin') // 模拟当前登录用户，防止删除自己

// 用户列表数据
const users = ref([])

// 表单数据模型
const form = reactive({
  id: null,
  username: '',
  password: '',
  email: '',
  role: '',
  active: true
})

// 表单验证规则
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

// --- 生命周期 ---
onMounted(() => {
  fetchUsers()
})

// --- 方法实现 ---

// 1. 获取用户列表 (模拟 API)
const fetchUsers = async () => {
  loading.value = true
  users.value = []
  try{
    const response = await fetch('http://localhost:8000/user/list', {
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
        for(const d of res.data) {
          users.value.push({
            id:d.id,
            username:d.username,
            email:d.email,
            active:d.is_active,
            role:d.role,
            password:''
          })
        }
      }else if(res.status === 'error'){
        ElMessage.error(res.message)
      }
      loading.value = false
  }catch(error){
    console.log(error)
    ElMessage.error(error)
    loading.value = false
  }
}

// 2. 点击创建按钮
const handleCreate = () => {
  isEdit.value = false
  dialogVisible.value = true
  // 表单重置在 @close 事件中处理
}

// 3. 点击修改按钮
const handleEdit = (row) => {
  isEdit.value = true
  dialogVisible.value = true
  
  // 将行数据复制到表单中
  // 注意：这里使用 Object.assign 进行浅拷贝，实际项目中可能需要深拷贝
  Object.assign(form, {
    id: row.id,
    username: row.username,
    email: row.email,
    role: row.role,
    active: row.active,
    password: '' // 编辑时密码默认为空
  })
}

// 4. 提交表单 (创建或修改)
const submitForm = () => {
  if (!formRef.value) return
  
  formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true

      if(isEdit.value) {
        try{
          const response = await fetch('http://localhost:8000/user/update', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
              },
              body:JSON.stringify({
                id:form.id,
                username: form.username,
                password: form.password,
                email: form.email,
                role: form.role,
                active: form.active
              })
            })
            if (!response.ok) {
              console.log(response)
              throw new Error(response.status);
            }
            const res = await response.json()
            if (res.status === 'success') {
              //users.value.push({ id: res.data.id, username:res.data.username, email: res.data.email, role: res.data.role,  active: res.data.active })
              ElMessage.success(res.message)
              fetchUsers()
              submitLoading.value = false
              dialogVisible.value = false
            }else if(res.status === 'error'){
              submitLoading.value = false
              ElMessage.error(res.message)
            }
        }catch(error){
          console.log(error)
          ElMessage.error(error)
        }
      }else{
        try{
          const response = await fetch('http://localhost:8000/user/create', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
              },
              body:JSON.stringify({
                username: form.username,
                password: form.password,
                email: form.email,
                role: form.role,
                active: form.active
              })
            })
            if (!response.ok) {
              console.log(response)
              throw new Error(response.status);
            }
            const res = await response.json()
            if (res.status === 'success') {
              //users.value.push({ id: res.data.id, username:res.data.username, email: res.data.email, role: res.data.role,  active: res.data.active })
              ElMessage.success(res.message)
              fetchUsers()
              submitLoading.value = false
              dialogVisible.value = false
            }else if(res.status === 'error'){
              submitLoading.value = false
              ElMessage.error(res.message)
            }
        }catch(error){
          console.log(error)
          ElMessage.error(error)
        }
      }
    }
  })
}

// 5. 删除用户
const handleDelete = (row) => {
  if (row.username === currentUser.value) {
    ElMessage.warning('不能删除当前登录账号')
    return
  }

  ElMessageBox.confirm(`确定要删除用户 "${row.username}" 吗？`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try{
      const response = await fetch('http://localhost:8000/user/delete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + localStorage.getItem('token')
          },
          body:JSON.stringify({
            username: row.username,
            id: row.id,
          })
        })
        if (!response.ok) {
          console.log(response)
          throw new Error(response.status);
        }
        const res = await response.json()
        if (res.status === 'success') {
          ElMessage.success("删除成功")
          fetchUsers()
        }else if(res.status === 'error'){
          ElMessage.error(res.message)
        }
    }catch(error){
      console.log(error)
      ElMessage.error(error)
    }
  }).catch(() => {})
}

// 6. 重置表单
const resetForm = () => {
  // if (formRef.value) {
  //   formRef.value.resetFields()
  // }
  // // 手动重置 reactive 对象中的值，确保 active 默认为 true
  // form.active = true
  // form.password = ''
  form.id = null
  form.username = ''
  form.email = ''
  form.password = ''
  form.role = 'user'
  form.active = true  
}
</script>

<style scoped>
.page {
  padding: 20px;
  background-color: #fff;
  border-radius: 4px;
}

.header {
  display: flex;
  justify-content: flex-start;
}
</style>