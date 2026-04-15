<template>
  <div class="page">
    <!-- 1. 顶部操作栏 -->
    <div class="header">
      <el-button type="primary" @click="handleUpload">
        <el-icon style="margin-right: 4px"><Upload /></el-icon>
        上传文件
      </el-button>
    </div>

    <!-- 2. 文件列表表格 -->
    <el-table :data="fileList" style="margin-top: 20px" border stripe v-loading="loading">
      <el-table-column prop="name" label="文件名" min-width="150" show-overflow-tooltip />
      <el-table-column prop="size" label="文件大小" width="120" />
      <!-- <el-table-column prop="path" label="文件路径" min-width="200" show-overflow-tooltip /> -->
      
      <el-table-column prop="category" label="类别" width="100">
        <template #default="{ row }">
          <el-tag :type="row.category === 'dept' ? 'warning' : 'success'" size="small">
            {{ row.category === 'dept' ? '部门' : '个人' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 0 ? 'warning' : 'success'" size="small">
            {{ row.status === 0 ? '未向量' : '已向量' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="deptName" label="所属部门" width="100" />
      <el-table-column prop="created_at" label="上传时间" width="180" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" :type="row.status === 0 ? 'success':'info'" @click="row.status === 0 ? handleIn(row) : handleOut(row)">
            {{ row.status === 0 ? '入库' : '出库' }}
          </el-button>
          <el-button size="small" type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 3. 上传/编辑 弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑文件信息' : '上传文件'" 
      width="500px"
      @close="resetForm"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        
        <!-- 文件选择 (仅在上传模式下显示) -->
        <el-form-item label="选择文件" prop="file" v-if="!isEdit">
          <el-upload
            ref="uploadRef"
            drag
            action="#" 
            :auto-upload="false"
            :limit="1"
            accept=".txt,.pdf"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处 或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                只能上传 txt / pdf 文件
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 文件属性 -->
        <el-form-item label="文件属性" prop="category">
          <el-radio-group v-model="form.category">
            <el-radio label="dept">部门</el-radio>
            <el-radio label="personal">个人</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 所属部门 (仅当属性为部门时显示) -->
        <el-form-item label="所属部门" prop="deptId" v-if="form.category === 'dept'">
          <el-select v-model="form.deptId" placeholder="请选择部门" style="width: 100%">
            <el-option 
            v-for="dept in deptList" 
            :key="dept.id" 
            :value="dept.id"
            :label="dept.name"
            >
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">
          {{ isEdit ? '保存修改' : '开始上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive ,onMounted} from 'vue'
import { Upload, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'


// --- 状态定义 ---
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const uploadRef = ref(null)
const deptList = ref([])

// 模拟文件列表数据
const fileList = ref([])

// 表单数据
const form = reactive({
  id: null,
  file: null, // 文件对象
  name: '',
  category: 'dept', // 默认选中部门
  deptId: null,
})

// 验证规则
const rules = {
  file: [{ required: true, message: '请选择文件', trigger: 'change' }],
  deptId: [
    { 
      required: true, 
      message: '请选择所属部门', 
      trigger: 'change',
      validator: (rule, value, callback) => {
        // 只有当属性是部门时才校验
        if (form.category === 'dept' && !value) {
          callback(new Error('请选择所属部门'))
        } else {
          callback()
        }
      }
    }
  ]
}
// --- 生命周期 ---
onMounted(() => {
  fetchDocs()
})
// --- 方法实现 ---
// 获取文档列表
const fetchDocs = async()=>{
  fileList.value = []
  loading.value = true
  try{
    const response = await fetch('http://localhost:8000/docs/list', {
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
        fileList.value.push(  
            { 
            id: d.id, 
            name: d.name, 
            size: formatSize(d.size), // 2.5MB
            //path: d.path, 
            category: d.category, 
            status:d.status,
            deptId: d.dept_id, 
            deptName: d.dept_name,
            created_at:d.created_at
            }
        )
      }
  }catch(error){
    ElMessage.error('获取列表失败')
  }finally{
    loading.value = false
  }
}
const fetchDept = async() =>{
  //获取部门列表
  try{
    deptList.value = []
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
        deptList.value.push({id: d.id, name: d.name})
      }
  }catch(error){
    ElMessage.error('获取列表失败')
  }
}
// 1. 点击上传按钮
const handleUpload = async() => {
  isEdit.value = false
  dialogVisible.value = true
  fetchDept()
}

// 2. 文件选择回调
const handleFileChange = (file) => {
  form.file = file.raw
  form.name = file.raw.name
}

// 3. 移除文件回调
const handleFileRemove = () => {
  form.file = null
  form.name = ''
}

// 4. 点击编辑按钮
const handleEdit = (row) => {
  isEdit.value = true
  dialogVisible.value = true
  fetchDept()
  // 回填数据
  form.id = row.id
  form.name = row.name
  form.category = row.category
  form.deptId = row.deptId
  // 编辑模式下不处理文件对象，只修改元数据
}

// 5. 提交表单
const submitForm = () => {
  if (!formRef.value) return
  
  formRef.value.validate(async (valid) => {
    if (valid) {
      // 上传模式下，如果没有选文件，提示错误
      if (!isEdit.value && !form.file) {
        ElMessage.warning('请先选择文件')
        return
      }

      submitLoading.value = true
        if (isEdit.value) {
            try{
            const response = await fetch('http://localhost:8000/docs/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                },
                body:JSON.stringify({id:form.id,category:form.category,dept_id:form.deptId})
                })
                if (!response.ok) {
                    console.log(response)
                    throw new Error(response.status);
                }
                const res = await response.json()
                if (res.status === 'success') {
                    //depts.value.push({ id: res.data.id, name: res.data.name })
                    // const index = depts.value.findIndex(item => item.id === form.id)
                    // if (index !== -1) {
                    //     depts.value[index].name = form.name
                    // }
                    fetchDocs()
                    ElMessage.success('修改成功。')
                }else if(res.status === 'error'){
                    ElMessage.error(res.message)
                }
            }catch(error){
                console.log(error)
                ElMessage.error(error)
            }finally{
                submitLoading.value = false
                dialogVisible.value = false 
            }
        } else {
            // 上传逻辑
            const formData = new FormData()
            formData.append('file',form.file)
            formData.append('category',form.category)
            formData.append('dept_id',form.deptId || 0)
            formData.append('name',form.name)
            formData.append('size',form.file.size)
            try{
                const response = await fetch('http://localhost:8000/docs/upload',{
                    method:'POST',
                    headers:{
                        'Authorization': 'Bearer '+localStorage.getItem('token')
                    },
                    body:formData
                })
                if (!response.ok){
                    throw new Error(response.status)
                }
                const res = await response.json()
                if (res.status === 'success') {
                    ElMessage.success('上传成功。')
                    fetchDocs()
                }else{
                    throw new Error(res.message)
                }
            }catch(error) {
                ElMessage.error('上传失败，'+error)
            }finally{
                submitLoading.value = false
                dialogVisible.value = false  
                //fileList.value.unshift(newFile)
            }
        }
    }
  })
}

// 6. 删除文件
const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除文件 "${row.name}" 吗？`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async() => {
    const index = fileList.value.findIndex(item => item.id === row.id)
    if (index !== -1) {
        try{
            const response = await fetch('http://localhost:8000/docs/delete?id='+row.id, {
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
                fileList.value.splice(index, 1)
                ElMessage.success('删除成功')
            }else if(res.status === 'error'){
                ElMessage.error(res.message)
            }
        }catch(error){
            console.log(error)
            ElMessage.error(error)
        }


    }
  }).catch(() => {})
}

// 7. 重置表单
const resetForm = () => {
  if (formRef.value) formRef.value.resetFields()
  if (uploadRef.value) uploadRef.value.clearFiles()
  form.file = null
  form.name = ''
}

// 辅助函数：格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

//入库
const handleIn = async (row)=>{
    try{
        loading.value = true
        const response = await fetch('http://localhost:8000/docs/in', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
            },
            body:JSON.stringify({id:row.id})
        })
        if (!response.ok) {
            console.log(response)
            throw new Error(response.status);
        }
        const res = await response.json()
        if (res.status === 'success') {
            fetchDocs()
            ElMessage.success(res.message)
        }else if(res.status === 'error'){
            ElMessage.error(res.message)
        }
    }catch(error){
        console.log(error)
        ElMessage.error(error)
    }finally{
        loading.value = false
    }
}

// 出库
const handleOut = async(row) =>{
    try{
        loading.value = true
        const response = await fetch('http://localhost:8000/docs/out', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
            },
            body:JSON.stringify({id:row.id})
        })
        if (!response.ok) {
            console.log(response)
            throw new Error(response.status);
        }
        const res = await response.json()
        if (res.status === 'success') {
            fetchDocs()
            ElMessage.success(res.message)
        }else if(res.status === 'error'){
            ElMessage.error(res.message)
        }
    }catch(error){
        console.log(error)
        ElMessage.error(error)
    }finally{
        loading.value = false
    }
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