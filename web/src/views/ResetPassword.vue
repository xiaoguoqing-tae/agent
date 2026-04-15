<template>
  <div class="reset-container">
    <!-- 左侧装饰背景 -->
    <div class="reset-banner">
      <div class="banner-content">
        <h1>重置密码</h1>
        <p>为了您的账户安全，请验证身份后设置新密码</p>
      </div>
    </div>

    <!-- 右侧表单区域 -->
    <div class="reset-form-wrapper">
      <div class="form-container">
        <div class="header">
          <h2>设置新密码</h2>
          <p>邮箱：{{ email }}</p>
        </div>

        <el-form :model="form" :rules="rules" ref="formRef" size="large">
          <el-form-item prop="code">
            <el-input v-model="form.code" placeholder="请输入验证码" prefix-icon="Key">
              <template #append>
                <el-button :disabled="countdown > 0" @click="handleResend">
                  {{ countdown > 0 ? `${countdown}s` : '重发' }}
                </el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item prop="newPassword">
            <el-input v-model="form.newPassword" type="password" placeholder="新密码" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-form-item prop="confirmPassword">
            <el-input v-model="form.confirmPassword" type="password" placeholder="确认新密码" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-button type="success" class="submit-btn" @click="handleReset" :loading="loading">
            确认修改
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
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const loading = ref(false)
const countdown = ref(0)
const email = ref('')
let timer = null // 用于清除定时器

const form = reactive({
  code: '',
  newPassword: '',
  confirmPassword: ''
})

// 页面加载时检查是否有邮箱参数
onMounted(() => {
  const queryEmail = route.query.email
  if (!queryEmail) {
    ElMessage.error('未检测到邮箱信息，请重新发起找回密码')
    router.push('/forgot-password')
  } else {
    email.value = queryEmail
    startCountdown() // 页面加载时开始倒计时
  }
})

// 组件卸载时清除定时器，防止内存泄漏
import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const rules = {
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== form.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

// 倒计时逻辑
const startCountdown = () => {
  if (timer) clearInterval(timer) // 防止重复开启
  countdown.value = 60
  timer = setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--
    } else {
      clearInterval(timer)
    }
  }, 1000)
}

// 重发验证码
const handleResend = () => {
  if (countdown.value > 0) return // 倒计时未结束，不允许点击
  
  // 模拟重新发送请求
  ElMessage.success('验证码已重新发送')
  startCountdown() // 重新开始倒计时
}

const handleReset = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 模拟后端接口调用
        // await request.post('/auth/forgot-password/reset', {
        //   email: email.value,
        //   code: form.code,
        //   new_password: form.newPassword
        // })
        
        ElMessage.success('密码修改成功，即将跳转登录')
        setTimeout(() => {
          router.push('/login')
        }, 1500)
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
.reset-container {
  display: flex;
  height: 100vh;
  width: 100%;
  background: #fff;
}

.reset-banner {
  flex: 0 0 55%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

.reset-form-wrapper {
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  .reset-banner {
    display: none;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>