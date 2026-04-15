import {ref} from 'vue'

export function request() {
    const baseURL = 'http://localhost:8000'
    const token = localStorage.getItem('token') || ''

    const fetchStream = async (endpoint,body,onMessage,onError,signal) =>{
        const headers = {
            'Content-Type': 'application/json',
        }

        if (token) {
            headers['Authorization'] = `Bearer ${token}`
        }
        try {
            const response = await fetch(`${baseURL}${endpoint}`,{
                method:'POST',
                headers,
                body:JSON.stringify(body),
                signal
            })

            if(response.status ===401){
                throw new Error('Unauthorized')
            }

            if(!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }

            const reader = response.body.getReader()
            const decoder = new TextDecoder('utf-8')

            // 缓冲区，处理数据块被截断的情况
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read();
                
                // 如果流结束，跳出循环
                if (done) break;

                buffer+=decoder.decode(value,{stream:true})

                // SSE 格式用 \n\n 分隔多条消息，这里分割处理
                const chunks = buffer.split('\n\n')
                
                // 最后一块可能不完整，留到下次处理
                buffer = chunks.pop() || ''

                //遍历完整块
                for(const chunk of chunks) {
                    // 每块可能有多行，按 \n 分割
                    const lines = chunk.split('\n')

                    for (const line of lines) {
                        // SSE 格式以 "data: " 开头
                        if (!line.startsWith('data: ')) continue

                        // 提取JSON字符串（去掉"data: "前缀）
                        const jsonStr = line.slice(6).trim()
                        if (!jsonStr || jsonStr === '[DONE]') continue
                        try{
                            const data = JSON.parse(jsonStr)
                            if(data.type === 'token' && data.content){
                                onMessage ?.(data.content) 
                            }
                            if(data.type === 'error') {
                                console.log('服务错误：'+data.content)
                            }
                        } catch(e) {
                            onMessage ?.(jsonStr)
                        }     
                    }
                }
            }

            // 处理缓冲区剩余内容
            if (buffer.trim()) {
                const lines = buffer.split('\n')
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6).trim()
                    try {
                        const data = JSON.parse(jsonStr)
                        if (data.type === 'token' && data.content) {
                            onMessage ?.(data.content)
                        }
                    } catch (e) {
                        onMessage ?.(jsonStr)
                    }
                    }
                }
            }
        } catch (error) {
            if(error.name === 'AbortError') {
                onMessage ?.('\n\n[已停止生成]')
            }else{
                onError?.(error)
                throw error
            }
        } finally {
            
        }
    }
    return {fetchStream}
}