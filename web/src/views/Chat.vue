<template>
  <div class="chat-page" @wheel="handleWheel">
    <!-- 消息列表区域 -->
    <div class="message-list" ref="messageListRef">
      <!-- 空状态 -->
      <div v-if="isNewChat && messages.length === 0" class="welcome-tips">
        <h2>你好，我是你的智能助手</h2>
        <p>今天可以帮你做些什么？</p>
      </div>

      <!-- 消息循环 -->
      <div v-else class="messages-container">
        <div v-for="(msg, index) in messages" :key="index" 
             :class="['message-item', msg.role]">
          
          <!-- human -->
          <template v-if="msg.role === 'human'">
            <div class="content-wrapper human">
              <div class="sender-name">你</div>
              <div class="message-content" v-html="msg.content"></div>
            </div>
            <div class="avatar-wrapper human">
              <div class="avatar human">
                <el-icon size="20"><User /></el-icon>
              </div>
            </div>            

          </template>
          
          <!-- AI -->
          <template v-else>
            <div class="avatar-wrapper ai">
              <div class="avatar ai" >
                <el-icon size="20"><Cpu /></el-icon>
              </div>
            </div>
            <div class="content-wrapper ai">
              <div class="sender-name">智能助手</div>
              <div class="message-content">
                <MarkdownRenderer :content="msg.content"/>
              </div>
            </div>
          </template>
        </div>
        
        <!-- 滚动到底部按钮 -->
        <div v-if="showScrollToBottom" class="scroll-to-bottom" @click="scrollToBottom">
          <el-icon><ArrowDownBold /></el-icon>
        </div>
      </div>
    </div>

    <!-- 底部输入框区域 -->
    <div class="input-area">
      <div class="input-box">
        <!-- 输入框区域 -->
        <div class="textarea-wrapper">
          <el-input 
            v-model="inputMessage" 
            type="textarea" 
            :autosize="{ minRows: 1, maxRows: 6 }"
            placeholder="发消息给智能助手..." 
            class="custom-textarea"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.enter.shift.exact="inputMessage += ''"
            :disabled="isStreaming"
          />
          
          <!-- 底部工具栏 -->
          <div class="toolbar">
            <div class="toolbar-left">
              <!-- 上传按钮 -->
              <el-button link class="tool-btn" title="上传文件">
                <el-icon><Paperclip /></el-icon>
              </el-button>

              <!-- 文档列表按钮 -->
              <el-popover
                v-model:visible="docPopoverVisible"
                placement="top-start"
                :width="300"
                trigger="click"
                popper-class="doc-list-popover"
              >
                <template #reference>
                  <!-- 核心修改：动态绑定类名，有选中文件时添加 has-selected -->
                  <el-button 
                    link 
                    class="tool-btn" 
                    :class="{ 'has-selected': selectedDocs.length > 0 }" 
                    title="文档列表"
                  >
                    <el-icon><Document /></el-icon>
                  </el-button>
                </template>
                
                <!-- 下拉框内容 -->
                <div class="doc-list-content">
                  <div class="doc-header">
                    <span>选择参考文档 ({{ selectedDocs.length }})</span>
                    <el-button link size="small" @click="selectAll">全选</el-button>
                  </div>
                  <el-checkbox-group v-model="selectedDocs" class="doc-checkbox-group">
                    <div v-for="doc in docList" :key="doc.id" class="doc-item">
                      <el-checkbox :value="doc.id" size="large">
                        <div class="doc-info">
                          <el-icon size="18" color="#667eea"><Document /></el-icon>
                          <div class="doc-text">
                            <div class="doc-name">{{ doc.name }}</div>
                            <div class="doc-size">{{ doc.size }}</div>
                          </div>
                        </div>
                      </el-checkbox>
                    </div>
                  </el-checkbox-group>
                </div>
              </el-popover>

              <!-- 更多按钮 -->
              <el-button link class="tool-btn" title="更多">
                <el-icon><Grid /></el-icon>
              </el-button>
            </div>
            
            <!-- 发送按钮 -->
            <div class="toolbar-right">
              <el-button type="primary" class="send-btn" @click="isStreaming ? stopGeneration() : sendMessage()" :loading="isLoading" :disabled="!isStreaming && !inputMessage.trim()">
              {{ isStreaming ? '⏹ 停止' : '➤ 发送' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
      <div class="footer-tip">
        内容由 AI 生成，请仔细甄别
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted,inject } from 'vue'
import { useRoute,useRouter} from 'vue-router'
import { ArrowDownBold } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import { request } from '@/composables/request'
import { jsonToStr,strToJson } from '@/utils/json'
const historyTitleList = inject('historyList')

const {fetchStream} = request()

const route = useRoute()
const router = useRouter()

const props = defineProps({
  currentChatId: { type: [String, Number], default: '' }
})

// 输入框里的文字
const inputMessage = ref('')

// 是否正在接收 AI 回复（控制加载动画、按钮状态）
const isLoading = ref(false)

// 是否正在流式接收中（控制停止按钮、渲染方式）
const isStreaming = ref(false)

// 用来取消请求的控制器（点击"停止"时用）
const abortController = ref(null)

const docPopoverVisible = ref(false)
const selectedDocs = ref([]) // 选中的文档ID数组
const messageListRef = ref(null)
const showScrollToBottom = ref(false)


const docList = ref([
  { id: 1, name: '扫地机器人100问.pdf', size: '2.4 MB' },

])

const messages = ref([])

const isNewChat = computed(() => props.currentChatId === '')

// 辅助函数：格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 获取历史消息
const getDocs = async()=> {
    try {
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

        // 4. 再次加上 await 并调用 .json() 解析实际数据
        const res = await response.json()
        docList.value = []
        if (res.status ==='success') {
          for(const d of res.data) {
            docList.value.push({ id: d.id, name: d.name,size:formatSize(d.size)})
          }
        }
    } catch (error) {
      console.log(error)
      ElMessage.error('请求出错:'+error)
    } 
}
// 获取历史消息
const getChatMessage = async(id)=> {
    try {
      const response = await fetch('http://localhost:8000/chat/message?id='+id, {
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
        messages.value = []
        for(const d of data) {
          messages.value.push({ role: d.role, content: d.content})
        }
        console.log("这是历史消息")
        console.log(data)
    } catch (error) {
      console.log(error)
      ElMessage.error('请求出错:'+error)
    } 
}

// --- 生命周期 ---
onMounted(() => {
  getDocs()
})


watch(()=>props.currentChatId,(chatId)=>{
  //判断是否新对话
  if (chatId ==="") {
    messages.value = []
    selectedDocs.value = []
  }else{
    
    const topic = strToJson(localStorage.getItem('chatTitle')) || null
    
    //无论有没有，都要把这个信息清空
    localStorage.removeItem('chatTitle')

    if(topic) {
      // 执行未处理的对话流
      streamMessage(topic.message)
    }else{
      //获取历史消息
      getChatMessage(chatId)
    }
  }
},{ immediate: true })


// 监听消息变化，自动滚动到底部
watch(messages, async () => {
  await nextTick()
  scrollToBottom()
}, { deep: true })

// 监听消息列表的滚动事件
const onScroll = () => {
  if (!messageListRef.value) return
  
  const { scrollTop, scrollHeight, clientHeight } = messageListRef.value
  // 当距离底部超过一定距离时显示回到底部按钮
  showScrollToBottom.value = scrollHeight - scrollTop - clientHeight > 100
}

// 滚动到底部
const scrollToBottom = () => {
  if (!messageListRef.value) return
  
  messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  showScrollToBottom.value = false
}


// 处理输入框滚动事件
const handleWheel = (e) => {
  if (messageListRef.value) {
    messageListRef.value.addEventListener('scroll', onScroll, { passive: true })
  }
}

const selectAll = () => {
  if (selectedDocs.value.length === docList.value.length) {
    selectedDocs.value = []
  } else {
    selectedDocs.value = docList.value.map(d => d.id)
  }
}


// ========== 停止生成 ==========
function stopGeneration() {
  if (abortController.value) {
    abortController.value.abort()
  }
}





// 聊天流
const streamMessage = async (userText)=>{

  //将用户消息加入列表
  messages.value.push({ role: 'human', content: userText });
  
  // 显示"正在输入"动画
  isLoading.value = true

  // 准备AI消息
  const aiMessage = ref({
    role: 'ai',
    content: ''
  })

  // AI消息加入到列表
  messages.value.push(aiMessage.value);
  
  // 加载动画结束，开始流式接收
  isLoading.value = false
  isStreaming.value = true

  // 创建取消控制器
  abortController.value = new AbortController()
  await fetchStream(
    '/chat',
    { messages: userText ,action:route.query.action || "",doc_ids:selectedDocs.value || []},
    (chunk) => {
      aiMessage.value.content+=chunk
    },
    (error)=>{
      aiMessage.value.content+=error
      isStreaming.value = false
    },
    abortController.value.signal
  )
  isStreaming.value = false
  abortController.value = null
}

// 按钮执行发送消息
const sendMessage = async () => {
  //拿到输入框内容，trim() 去掉首尾空格
  const userText = inputMessage.value.trim();

  // 如果输入为空，直接返回不处理
  if (!userText || isStreaming.value) return;

  // 清空输入框，准备接收下一条
  inputMessage.value = ''  

  // 如果是新对话，把对话内容发至服务器，服务器产生对话ID与话题返回客户端
  if (isNewChat.value) {
    try {
      const response = await fetch('http://localhost:8000/chat/title', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + localStorage.getItem('token')
            },
            body: JSON.stringify({ message: userText}),
          })
        
        if (!response.ok) {
          throw new Error('网络响应错误: ' + response.status);
        }

        // 4. 再次加上 await 并调用 .json() 解析实际数据
        const data = await response.json()

        // 把返回ID与对话主题存入浏览器，然后跳转到历史，历史检测 topic，如果有则请求输出
        localStorage.setItem('chatTitle',JSON.stringify(data))
        historyTitleList.value.push({id:data.id,title:data.title})
        router.push('/chat?action='+data.id)
    } catch (error) {
      ElMessage.error('请求出错:'+error)
    }      
  }else{
    // 不是新对话，直接在当前主题下输出内容
    streamMessage(userText)
  }
}
</script>

<style scoped>
/* --- 整体布局 --- */
.chat-page { height: 100%; display: flex; flex-direction: column; background-color: #fff; }
.message-list { 
  flex: 1; 
  overflow-y: auto; 
  padding: 20px 0; 
  scroll-behavior: smooth;
  /* 自定义滚动条样式 */
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 #f1f1f1;
}
.message-list::-webkit-scrollbar {
  width: 6px;
}
.message-list::-webkit-scrollbar-track {
  background: #f1f1f1;
}
.message-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}
.message-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.welcome-tips { text-align: center; padding-top: 10vh; color: #303133; }
.welcome-tips h2 { font-weight: 500; margin-bottom: 10px; }
.welcome-tips p { color: #909399; }

/* 消息容器 - 与输入框宽度一致 */
.messages-container { 
  max-width: 900px; 
  margin: 0 auto; 
  padding: 0 20px; 
  width: 100%;
  position: relative;
}

/* --- 消息样式 --- */
.message-item { 
  display: flex; 
  margin-bottom: 30px; 
  line-height: 1.6; 
  align-items: flex-start;
  width: 100%;
}
.message-item.ai { 
  justify-content: flex-start; /* AI消息：靠左对齐 */
}
.message-item.human { 
  justify-content: flex-end; /* 用户消息：靠右对齐 */
}

.avatar-wrapper { 
  flex-shrink: 0; 
  display: flex;
  align-items: flex-start;
  margin-top: 4px;
}
.avatar-wrapper.ai { 
  margin-right: 12px; 
}
.avatar-wrapper.human { 
  margin-left: 12px; 
}

.avatar { 
  width: 36px; 
  height: 36px; 
  border-radius: 50%; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  color: #fff; 
}
.avatar.ai { 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
}
.avatar.human { 
  background-color: #dcdfe6; 
  color: #606266; 
}

.content-wrapper { 
  display: inline-block;
  max-width: calc(100% - 80px); /* 减去头像和间距的总宽度 */
  word-wrap: break-word;
  word-break: break-word;
  vertical-align: top;
}

.sender-name { 
  font-size: 14px; 
  font-weight: 600; 
  margin-bottom: 6px; 
  color: #303133; 
}

/* AI消息样式 - 不需要气泡 */
.message-item.ai .content-wrapper {
  text-align: left;
  background: transparent;
  padding: 0;
  border-radius: 0;
}
.message-item.ai .content-wrapper::before {
  display: none; /* 隐藏AI消息的三角形 */
}
.message-item.ai .sender-name {
  text-align: left;
}

/* 用户消息气泡样式 - 宽度随内容自适应 */
.message-item.human .content-wrapper {
  text-align: left;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 16px;
  border-radius: 18px;
  border-top-right-radius: 4px;
  min-width: 100px; /* 最小宽度 */
  max-width: 75%;
  position: relative;
  margin-right: 12px; /* 与头像的间距 */
}
.message-item.human .content-wrapper::before {
  content: '';
  position: absolute;
  right: -8px;
  top: 10px;
  width: 0;
  height: 0;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  border-left: 8px solid #667eea;
}
.message-item.human .sender-name{
  color: white !important;
}
.message-item.human .sender-name {
  text-align: left;
}

/* --- 回到底部按钮 --- */
.scroll-to-bottom {
  position: sticky;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dcdfe6;
  border-radius: 50%;
  cursor: pointer;
  z-index: 10;
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: all 0.3s ease;
}
.scroll-to-bottom:hover {
  background: #fff;
  transform: translateX(-50%) scale(1.1);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.scroll-to-bottom .el-icon {
  color: #667eea;
  font-size: 18px;
}

/* --- 底部输入框 --- */
.input-area { 
  padding: 20px; 
  background: #fff; 
  display: flex; 
  flex-direction: column; 
  align-items: center; 
  /*border-top: 1px solid #f0f2f5;*/
}

.input-box {
  width: 100%;
  max-width: 900px;
  background: #f4f4f5;
  border-radius: 12px;
  padding: 12px 16px;
  transition: all 0.3s;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}

.input-box:focus-within {
  background: #fff;
  border: 1px solid #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.textarea-wrapper { position: relative; width: 100%; }

.custom-textarea :deep(.el-textarea__inner) {
  background: transparent;
  box-shadow: none !important;
  resize: none;
  padding: 4px 0 30px 0;
  font-size: 15px;
  line-height: 1.5;
  overflow-y: auto;
  scrollbar-width: none;
  border: none !important;
}
.custom-textarea :deep(.el-textarea__inner)::-webkit-scrollbar { display: none; }

/* --- 工具栏 --- */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  height: 32px;
}

.toolbar-left { display: flex; gap: 4px; }
.toolbar-right { display: flex; }

.tool-btn {
  color: #909399;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
}

.tool-btn:hover { 
  background-color: #f0f2f5; 
  color: #667eea; 
}

/* 核心修改：选中状态样式 - 给文档按钮加紫色背景和白色文字 */
.tool-btn.has-selected {
  background-color: #667eea;
  color: #fff;
}
.tool-btn.has-selected:hover {
  background-color: #5a6fd6;
  color: #fff;
}

.send-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  padding: 8px 20px;
  height: auto;
  font-weight: 500;
}
.send-btn:hover { opacity: 0.9; }
.send-btn:disabled { background: #dcdfe6; cursor: not-allowed; }

.footer-tip { margin-top: 10px; font-size: 12px; color: #c0c4cc; }

/* --- 文档列表弹窗样式 --- */
.doc-list-content { max-height: 300px; overflow-y: auto; }
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}
.doc-checkbox-group { display: flex; flex-direction: column; gap: 8px; }
.doc-item { padding: 4px 0; }
.doc-info { display: flex; align-items: center; gap: 10px; }
.doc-text { display: flex; flex-direction: column; }
.doc-name { font-size: 14px; color: #303133; }
.doc-size { font-size: 12px; color: #909399; margin-top: 2px; }
</style>