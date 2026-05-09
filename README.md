# 大模型应用开发练习
 - 这是我学习完大模型 RAG与Agent之后的一个练习项目 chain，希望对刚学习的朋友有一点帮助
 - 本项目是前后端分离项目，后台使用 Python+FastAPI+Langchain1.x+Sqlite3 ，前端使用 Vue3+element-plus
# 后台版本与依赖
- Python 3.10+
- langchain1.x


`依赖包，最好使用 conda 环境，如果使用 conda 可以执行以下代码，不使用 conda 直接执行以下的 “安装依赖包”`
- 1.创建conda环境
  ```
  conda create -n llm python=3.10.4
  ```
- 2.激活conda llm 环境
  ```
  conda activate llm
  ```  

`安装依赖包 ** 无论是否使用conda环境，都需要安装以下依赖 ** `
```bash
pip install langchain
pip install langchain-community
pip install langchain_chroma
pip install dashscope
pip install fastapi
pip install uvicorn
pip install pypdf
pip install aiosqlite
pip install "python-jose[cryptography]" bcrypt
pip install "passlib[bcrypt,argon2,scrypt,totp]"
pip install python-multipart
pip install "bcrypt<4.1.0"
```
# 配置
根目录配置文件 config.yaml,只需要修改大模型与模型的密钥即可使用
```yaml
#======大语言模型=====
chat:
  model: qwen3-max
  api_key: sk-你的百炼平台的key

#向量模型
embedding:
  model: text-embedding-v4
  dashscope_api_key: sk-你的百炼平台的key

```
# 启动后台服务
进入项目 chain/service 执行以下代码启动服务
```bash
cd /chain/service

uvicorn main:app --reload
```
- 使用默认端口 8000
- 前台Vue3访问 http://localhost:8000

# 前台启动
进入项目 chain/web 执行以下代码启动服务
```bash
cd /chain/web
npm install
npm run dev
```
- 访问前台链接：http://localhost:5173
