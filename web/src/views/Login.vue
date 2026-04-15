<template>
  <div class="login-container">
    <!-- 左侧装饰背景 -->
    <div class="login-banner">
      <div class="banner-content">
        <h1>欢迎回来</h1>
        <p>请登录您的账户以继续</p>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-form-wrapper">
      <div class="form-container">
        <div class="header">
          <h2>用户登录</h2>
          <p>请输入您的账号和密码</p>
        </div>

        <el-form 
          ref="loginFormRef" 
          :model="loginForm" 
          :rules="rules" 
          class="login-form"
        >
          <el-form-item prop="username">
            <el-input 
              v-model="loginForm.username" 
              placeholder="请输入用户名" 
              prefix-icon="User"
              size="large"
              clearable
            />
          </el-form-item>
          
          <el-form-item prop="password">
            <el-input 
              v-model="loginForm.password" 
              type="password" 
              placeholder="请输入密码" 
              prefix-icon="Lock"
              size="large"
              show-password
            />
          </el-form-item>

          <!-- 修改点：使用 to 属性，这是 Element Plus 官方推荐的导航写法 -->
          <div class="form-options" style="display: flex; justify-content: space-between; align-items: center;">
            <el-checkbox v-model="remember">记住密码</el-checkbox>
            <el-link type="primary" underline="never" @click="router.push('/forgot-password')">
              忘记密码？
            </el-link>
          </div>

          <el-form-item>
            <el-button 
              type="primary" 
              class="login-btn" 
              size="large" 
              :loading="loading" 
              @click="handleLogin"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)
const remember = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const response = await fetch('http://localhost:8000/login', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ username: loginForm.username,password:loginForm.password}),
            })
          if (!response.ok) {
            throw new Error('网络响应错误: ' + response.status);
          }

          const res = await response.json()
          if (res.status === 'success') {
            ElMessage.success('登录成功')
            localStorage.setItem('token', res.data.token)
            localStorage.setItem('username', res.data.username)
            localStorage.setItem('userRole', res.data.role)            
            //router.push('/chat')
            window.location.replace('/chat')
          }else{
            ElMessage.error(res.message)
          }
      } catch (error) {
        ElMessage.error(error || '登录失败，请检查网络')
      }finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  height: 100vh;
  width: 100%;
  background: #fff;
}
.login-banner {
  flex: 0 0 55%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}
.banner-content { text-align: center; animation: fadeIn 1s ease-in; }
.banner-content h1 { font-size: 48px; font-weight: 300; margin-bottom: 16px; }
.banner-content p { font-size: 18px; opacity: 0.9; }
.login-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 40px;
  box-sizing: border-box;
}
.form-container { width: 100%; max-width: 360px; }
.header { margin-bottom: 40px; text-align: center; }
.header h2 { font-size: 28px; color: #303133; margin-bottom: 8px; }
.header p { color: #909399; font-size: 14px; }
.login-form { margin-bottom: 0; }
.login-btn {
  width: 100%; height: 44px; font-size: 16px; font-weight: 500;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}
@media (max-width: 768px) { .login-banner { display: none; } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>