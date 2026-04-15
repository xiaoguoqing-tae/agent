import { createRouter, createWebHistory } from 'vue-router'
const routes = [
  // 公开页面
  { 
    path: '/login', 
    component:()=>import('@/views/Login.vue'), 
    meta: { public: true, title: '用户登录' } 
  },
  { 
    path: '/forgot-password', 
    component: ()=>import('@/views/ForgotPassword.vue') ,
    meta:{public:true,title:"忘记密码"}
  },
  { 
    path: '/reset-password',
    component: ()=>import('@/views/ResetPassword.vue') ,
    meta:{public:true,title:"重置密码"}
  },

  {
    path:'/',
    component:()=>import('@/components/Main.vue'),
    redirect:'/chat',
    children:[
      {
        path:'chat',
        component:()=>import('@/views/Chat.vue'),
        meta:{title:'智能对话'}
      },
      {
        path:'users',
        component:()=>import('@/views/UserManage.vue'),
        meta:{title:'用户管理'}
      },    
      {
        path:'depts',
        component:()=>import('@/views/DeptManage.vue'),
        meta:{title:'部门管理'}
      },    
      {
        path:'docs',
        component:()=>import('@/views/Docs.vue'),
        meta:{title:'文档管理'}
      },                 
    ]
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：处理标题和权限
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  // 设置页面标题
  document.title = to.meta.title || '智能对话系统'

  if (!token && !to.meta.public) {
    next('/login')
  }else if (token && to.path === '/login') {
    next('/')
  }else{
    next()
  }
})

export default router