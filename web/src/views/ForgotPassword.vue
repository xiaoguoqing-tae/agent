<template>
  <div class="forgot-container">
    <!-- 左侧装饰背景 -->
    <div class="forgot-banner">
      <div class="banner-content">
        <h1>账号安全</h1>
        <p>请输入您的注册邮箱以获取重置验证码</p>
      </div>
    </div>

    <!-- 右侧表单区域 -->
    <div class="forgot-form-wrapper">
      <div class="form-container">
        <div class="header">
          <h2>找回密码</h2>
          <p>我们将发送一封验证邮件到您的邮箱</p>
        </div>

        <el-form :model="form" :rules="rules" ref="formRef" size="large">
          <el-form-item prop="email">
            <el-input 
              v-model="form.email" 
              placeholder="请输入注册邮箱" 
              prefix-icon="Message"
              clearable
            />
          </el-form-item>
          
          <el-button type="primary" class="submit-btn" @click="handleSendCode" :loading="loading">
            发送验证码
          </el-button>
        </el-form>

        <div class="footer">
          <el-link type="primary" underline="never" @click="router.push('/login')">
            <el-icon><ArrowLeft /></el-icon> 返回登录
          </el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  email: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

const handleSendCode = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 模拟后端接口调用
        // await request.post('/auth/forgot-password/send-code', { email: form.email })
        
        ElMessage.success('验证码已发送，请查收邮箱')
        
        // 核心修改：跳转到第二步页面，并把邮箱作为参数带过去
        router.push({ path: '/reset-password', query: { email: form.email } })
        
      } catch (e) {
        console.error(e)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.forgot-container {
  display: flex;
  height: 100vh;
  width: 100%;
  background: #fff;
}

.forgot-banner {
  flex: 0 0 55%;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.banner-content {
  text-align: center;
  animation: fadeIn 1s ease-in;
}

.banner-content h1 {
  font-size: 48px;
  font-weight: 300;
  margin-bottom: 16px;
  letter-spacing: 2px;
}

.banner-content p {
  font-size: 18px;
  opacity: 0.9;
}

.forgot-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 40px;
  box-sizing: border-box;
}

.form-container {
  width: 100%;
  max-width: 360px;
}

.header {
  margin-bottom: 40px;
  text-align: center;
}

.header h2 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 8px;
  font-weight: 500;
}

.header p {
  color: #909399;
  font-size: 14px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border: none;
  transition: all 0.3s ease;
}

.submit-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.footer {
  margin-top: 20px;
  text-align: center;
}

@media (max-width: 768px) {
  .forgot-banner {
    display: none;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>