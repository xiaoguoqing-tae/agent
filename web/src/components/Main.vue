<template>
  <!-- 主布局 -->
  <el-container class="layout-container">
    
    <!-- 左侧侧边栏：恢复渐变色背景 -->
    <el-aside width="260px" class="aside">
      <!-- 顶部 Logo 区域 -->
      <div class="logo-area">
        <div class="logo-content">
          <el-icon size="24"><Histogram /></el-icon>
          <span>智能对话系统</span>
        </div>
        <!-- 新对话按钮 -->
        <el-button class="new-chat-btn" @click="createNewChat">
          <el-icon><Plus /></el-icon>
          <span>新建对话</span>
        </el-button>
      </div>

      <!-- 菜单列表 -->
      <div class="menu-container">
        <div class="menu-group-title">最近的话题</div>
        
        <!-- 历史会话列表 -->
        <el-menu 
          class="side-menu" 
          :default-active="activeMenu" 
          mode="vertical"
        >
          <el-menu-item 
            v-for="topic in historyList" 
            :key="topic.id" 
            :index="String(topic.id)"
            class="history-menu-item"
          >
            <div class="topic-content" @click.stop="enterTopic(topic.id)">
              <el-icon><ChatLineRound /></el-icon>
              <span class="topic-title">{{ topic.title }}</span>
            </div>
            <!-- 操作按钮 -->
            <el-dropdown trigger="click" @command="(cmd) => handleTopicCommand(cmd, topic)">
              <el-button link class="topic-action">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="delete" style="color: #f56c6c">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </el-menu-item>
        </el-menu>

        <!-- 底部管理员菜单 -->
        <div v-if="userRole === 'admin'" class="admin-menu">
          <div class="menu-group-title">系统管理</div>
          <el-menu class="side-menu" mode="vertical">
             <el-menu-item index="/users" @click="router.push('/docs')">
              <el-icon><Document /></el-icon>
              <span>文档管理</span>
            </el-menu-item>            
             <el-menu-item index="/users" @click="router.push('/users')">
              <el-icon><User /></el-icon>
              <span>账号管理</span>
            </el-menu-item>
            <el-menu-item index="/depts" @click="router.push('/depts')">
              <el-icon><OfficeBuilding /></el-icon>
              <span>部门管理</span>
            </el-menu-item>
          </el-menu>
        </div>
      </div>
    </el-aside>
    <!-- 右侧内容区 -->
    <el-container class="right-container">
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-content">
          <div class="page-title">
            <span>{{ route.meta.title }}</span>
          </div>
          
          <!-- 用户信息 -->
          <div class="user-info">
            <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
            <span class="username">{{ userRole === 'admin' ? '管理员' : '普通用户' }}</span>
            <el-divider direction="vertical" />
            <el-button link class="logout-btn" @click="handleLogout">退出</el-button>
          </div>
        </div>
      </el-header>

      <el-main class="main">
        <router-view :currentChatId="currentChatId"/>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed,onMounted,provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userRole = localStorage.getItem('userRole')||ref('user')
const historyList = ref([])

const currentChatId = computed(() => route.query.action || '')
const activeMenu = computed(() => route.query.action || '')
const isNewChat = computed(() => currentChatId.value === '')

const createNewChat = () => {
  router.push({ path: '/chat'})
}

const enterTopic = (id) => {
  router.push({ path: '/chat', query: { action: id } })
}

provide('historyList',historyList)



onMounted(async ()=>{
  // if (route.meta.public)return

  //获取对话列表
  try {
    const response = await fetch('http://localhost:8000/chat/list', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + localStorage.getItem('token')
          },
        })
      
      if (!response.ok) {
        throw new Error('网络响应错误: ' + response.status);
      }

      // 4. 再次加上 await 并调用 .json() 解析实际数据
      const data = await response.json()

      for (const d of  data) {
        historyList.value.push({id:d.id,title:d.title})
      }
  } catch (error) {
    console.log(error)
    ElMessage.error('请求出错:'+error)
  } 
})

// chat 删除
const deleteChat = async(chatId)=>{
  try{
    const response = await fetch('http://localhost:8000/chat/delete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + localStorage.getItem('token'),
          },
          body:JSON.stringify({id:chatId})
        })
      
      if (!response.ok) {
        throw new Error('网络响应错误: ' + response.status);
      }

      // 4. 再次加上 await 并调用 .json() 解析实际数据
      const data = await response.json()

      if (data.status === 'success') {
        historyList.value = historyList.value.filter(t => t.id !== chatId)
        if (currentChatId.value === chatId) createNewChat()
        ElMessage.success('删除成功')
        if (route.path === '/chat') {
          router.push('/chat')
        }
      }
  } catch (error) {
    console.log(error)
    ElMessage.error('请求出错:'+error)
  } 
}
// chat 重命名
const renameChat = async(chatId,title)=>{
  try{
    const response = await fetch('http://localhost:8000/chat/rename', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + localStorage.getItem('token'),
          },
          body:JSON.stringify({id:chatId,title:title})
        })
      
      if (!response.ok) {
        throw new Error('网络响应错误: ' + response.status);
      }

      // 4. 再次加上 await 并调用 .json() 解析实际数据
      const data = await response.json()

      if (data.status === 'success') {
        const item = historyList.value.find(item=>item.id === chatId)
        if (item){
          item.title = title
          ElMessage.success('重命名成功')
        }
      }
  } catch (error) {
    console.log(error)
    ElMessage.error('请求出错:'+error)
  } 
}

// chat 主题操作
const handleTopicCommand = (command, topic) => {
  if (command === 'delete') {
    ElMessageBox.confirm(`确定要删除会话 "${topic.title}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }).then(() => {
      deleteChat(topic.id)
    }).catch(() => {})
  } else if (command === 'rename') {
    ElMessageBox.prompt('请输入新的会话名称', '重命名', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: topic.title,
    }).then(({ value }) => {
      renameChat(topic.id,value)
    }).catch(() => {})
  }
}

// 退出登录
const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userRole')
  localStorage.removeItem('username')
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
/* --- 整体布局 --- */
.layout-container {
  height: 100vh;
  background-color: #f7f7f8;
}
.right-container { display: flex; flex-direction: column; height: 100%; }

/* --- 侧边栏设计 --- */
.aside {
  /* 核心修改：恢复原来的渐变色背景 */
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  padding: 12px;
  box-sizing: border-box;
  flex-shrink: 0;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
}

/* Logo 区域 */
.logo-area {
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  margin-bottom: 10px;
}
.logo-content {
  display: flex;
  align-items: center;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-left: 10px;
}
.logo-content .el-icon { margin-right: 10px; }

/* 新建对话按钮 */
.new-chat-btn {
  width: 100%;
  background-color: #fff;
  color: #764ba2; /* 按钮文字颜色改为紫色系 */
  border: none;
  border-radius: 8px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
  transition: all 0.2s;
}
.new-chat-btn:hover {
  background-color: #f0f0f0;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

/* 菜单容器 */
.menu-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
.menu-container::-webkit-scrollbar { width: 4px; }
.menu-container::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 2px; }

.menu-group-title {
  padding: 10px 10px 5px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 600;
}

/* 侧边栏菜单 */
.side-menu {
  background-color: transparent;
  border-right: none;
}
.side-menu .el-menu-item {
  /*height: auto;*/
  padding: 0;
  margin-bottom: 4px;
  border-radius: 8px;
}

/* 历史会话项 */
.history-menu-item.is-active {
  background-color: rgba(255, 255, 255, 0.2);
}
.history-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.topic-content {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 10px 12px;
  color: rgba(255, 255, 255, 0.9);
  overflow: hidden;
}
.topic-content .el-icon { margin-right: 10px; font-size: 16px; }
.topic-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
}

.topic-action {
  opacity: 0;
  color: rgba(255, 255, 255, 0.7);
  padding: 8px;
  height: auto;
}
.history-menu-item:hover .topic-action { opacity: 1; }
.topic-action:hover { color: #fff; }

/* 底部管理员菜单 */
.admin-menu { margin-top: 20px; }
.admin-menu .side-menu .el-menu-item {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}
.admin-menu .side-menu .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* --- 顶部导航栏 --- */
.header {
  background-color: #fff;
  border-bottom: 1px solid #e5e5e5;
  padding: 0 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title { font-size: 16px; font-weight: 600; color: #333; }

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #333;
}
.username { font-weight: 500; }
.logout-btn { color: #999; }
.logout-btn:hover { color: #f56c6c; }

/* --- 主内容区 --- */
.main {
  background-color: #fff;
  padding: 0;
  overflow: hidden;
  height: 100%;
}
</style>