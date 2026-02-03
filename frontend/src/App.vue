<template>
  <div class="app">
    <header class="header">
      <h1>📱 SMS Viewer</h1>
      <p>SMSToMe.com 手机号短信查询</p>
      <div class="connection-status" :class="{ connected: isConnected, disconnected: !isConnected }">
        {{ isConnected ? '✅ 已连接' : '❌ 未连接' }}
      </div>
    </header>

    <main class="main">
      <!-- 搜索区域 -->
      <div class="search-section">
        <div class="search-box">
          <select v-model="selectedCountry" class="country-select">
            <option v-for="(slug, code) in countries" :key="code" :value="slug">
              {{ countryNames[code] || code }}
            </option>
          </select>
          <input
            v-model="searchPhone"
            type="text"
            placeholder="输入手机号搜索 (如: 447447283220)"
            class="search-input"
            @keyup.enter="searchPhoneSMS"
          />
          <button @click="searchPhoneSMS" :disabled="loading" class="btn btn-primary">
            {{ loading ? '搜索中...' : '搜索短信' }}
          </button>
        </div>
      </div>

      <!-- 标签页 -->
      <div class="tabs">
        <button
          :class="['tab', { active: activeTab === 'list' }]"
          @click="activeTab = 'list'"
        >
          📋 手机号列表
        </button>
        <button
          :class="['tab', { active: activeTab === 'sms' }]"
          @click="activeTab = 'sms'"
        >
          📨 短信详情
        </button>
        <button
          :class="['tab', { active: activeTab === 'api' }]"
          @click="activeTab = 'api'"
        >
          📖 API 文档
        </button>
        <button
          :class="['tab', { active: activeTab === 'settings' }]"
          @click="activeTab = 'settings'; loadCookies()"
        >
          ⚙️ 设置
        </button>
      </div>

      <!-- 手机号列表 -->
      <div v-if="activeTab === 'list'" class="panel">
        <div class="panel-header">
          <h2>手机号列表 - {{ selectedCountry }}</h2>
          <div class="pagination">
            <button @click="prevPage" :disabled="currentPage <= 1 || loading" class="btn btn-sm">
              ◀ 上一页
            </button>
            <span class="page-info">第 {{ currentPage }} 页</span>
            <button @click="nextPage" :disabled="!hasMore || loading" class="btn btn-sm">
              下一页 ▶
            </button>
            <button @click="loadPhones" :disabled="loading" class="btn btn-sm btn-primary">
              🔄 刷新
            </button>
          </div>
        </div>

        <div v-if="loading" class="loading">加载中...</div>
        
        <div v-else-if="phones.length" class="phone-list">
          <div
            v-for="phone in phones"
            :key="phone.phone"
            class="phone-card"
            @click="viewPhoneSMS(phone)"
          >
            <div class="phone-number">
              <span v-if="phone.is_new" class="badge new">NEW</span>
              {{ phone.phone }}
            </div>
            <div class="phone-info">
              <span class="time">⏰ {{ phone.added_time }}</span>
            </div>
          </div>
        </div>

        <div v-else class="empty">暂无数据，点击刷新加载</div>
      </div>

      <!-- 短信详情 -->
      <div v-if="activeTab === 'sms'" class="panel">
        <div class="panel-header">
          <h2>短信详情</h2>
          <div v-if="currentPhoneDetail" class="phone-meta">
            <span>📞 {{ currentPhoneDetail.phone }}</span>
            <span>📍 {{ currentPhoneDetail.country }}</span>
            <span>⏰ {{ currentPhoneDetail.added_time }}</span>
          </div>
        </div>

        <div v-if="loadingSMS" class="loading">加载短信中...</div>

        <div v-else-if="currentPhoneDetail && currentPhoneDetail.messages.length" class="sms-list">
          <div v-for="(msg, index) in currentPhoneDetail.messages" :key="index" class="sms-card">
            <div class="sms-header">
              <span class="sender">📨 {{ msg.sender }}</span>
              <span class="time">{{ msg.received_time }}</span>
            </div>
            <div class="sms-content">{{ msg.message }}</div>
          </div>
        </div>

        <div v-else class="empty">
          请从列表选择手机号或搜索手机号查看短信
        </div>
      </div>

      <!-- API 文档 -->
      <div v-if="activeTab === 'api'" class="panel">
        <div class="panel-header">
          <h2>📖 API 接口文档</h2>
          <span class="api-base">Base URL: <code>http://localhost:5001</code></span>
        </div>

        <div class="api-docs">
          <!-- 获取手机号 -->
          <div class="api-section">
            <h3>📱 获取手机号列表</h3>
            
            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/phones/{country}</code>
              <p class="api-desc">获取指定国家的手机号列表</p>
              <div class="api-params">
                <h4>参数:</h4>
                <ul>
                  <li><code>country</code> - 国家代码: uk, poland, netherlands, sweden, finland, belgium, slovenia</li>
                  <li><code>page</code> - 页码 (默认 1)</li>
                  <li><code>pages</code> - 多页获取，如 <code>1,2,3</code> 或 <code>1-5</code></li>
                  <li><code>all</code> - 获取所有页 (true/false)</li>
                </ul>
              </div>
              <div class="api-examples">
                <h4>示例:</h4>
                <pre>GET /api/phones/uk              # 第一页
GET /api/phones/uk?page=2       # 第二页
GET /api/phones/uk?pages=1-3    # 1-3页
GET /api/phones/uk?all=true     # 所有页</pre>
              </div>
            </div>

            <div class="api-item">
              <div class="api-method get">GET</div>
              <div class="api-method post">POST</div>
              <code class="api-url">/api/phones</code>
              <p class="api-desc">批量获取多国家多页手机号</p>
              <div class="api-examples">
                <h4>GET 示例:</h4>
                <pre>GET /api/phones?country=uk,poland&pages=1-3</pre>
                <h4>POST 示例:</h4>
                <pre>{
  "countries": ["uk", "poland"],
  "pages": [1, 2, 3]
}</pre>
              </div>
            </div>
          </div>

          <!-- 获取短信 -->
          <div class="api-section">
            <h3>📨 获取短信</h3>
            
            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/sms/{phone}</code>
              <p class="api-desc">简化接口 - 获取手机号短信</p>
              <div class="api-params">
                <h4>参数:</h4>
                <ul>
                  <li><code>phone</code> - 手机号 (不含+)</li>
                  <li><code>country</code> - 国家代码 (默认 uk)</li>
                  <li><code>limit</code> - 返回条数 (默认 1，0=全部)</li>
                </ul>
              </div>
              <div class="api-examples">
                <h4>示例:</h4>
                <pre>GET /api/sms/447454414630           # 最新1条
GET /api/sms/447454414630?limit=5   # 最新5条
GET /api/sms/447454414630?limit=0   # 全部</pre>
              </div>
            </div>

            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/phone/{phone}/sms</code>
              <p class="api-desc">详细接口 - 获取手机号短信</p>
              <div class="api-params">
                <h4>参数:</h4>
                <ul>
                  <li><code>country</code> - 国家代码 (默认 uk)</li>
                  <li><code>pages</code> - 短信页数 (默认 1)</li>
                  <li><code>limit</code> - 返回条数限制</li>
                  <li><code>latest</code> - 只返回最新一条 (true/false)</li>
                </ul>
              </div>
              <div class="api-examples">
                <h4>示例:</h4>
                <pre>GET /api/phone/447454414630/sms?latest=true
GET /api/phone/447454414630/sms?limit=10
GET /api/phone/447454414630/sms?pages=3</pre>
              </div>
            </div>
          </div>

          <!-- 搜索和缓存 -->
          <div class="api-section">
            <h3>🔍 搜索和缓存</h3>
            
            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/search/{country}/{phone}</code>
              <p class="api-desc">搜索手机号，返回详情页 URL</p>
            </div>

            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/cache</code>
              <p class="api-desc">获取 URL 缓存列表</p>
            </div>

            <div class="api-item">
              <div class="api-method delete">DELETE</div>
              <code class="api-url">/api/cache/{phone}</code>
              <p class="api-desc">删除指定手机号的缓存</p>
            </div>
          </div>

          <!-- 系统接口 -->
          <div class="api-section">
            <h3>⚙️ 系统接口</h3>
            
            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/health</code>
              <p class="api-desc">健康检查</p>
            </div>

            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/countries</code>
              <p class="api-desc">获取支持的国家列表</p>
            </div>

            <div class="api-item">
              <div class="api-method get">GET</div>
              <code class="api-url">/api/cookies</code>
              <p class="api-desc">查看当前 Cookies</p>
            </div>

            <div class="api-item">
              <div class="api-method post">POST</div>
              <code class="api-url">/api/cookies</code>
              <p class="api-desc">设置 Cookies</p>
            </div>

            <div class="api-item">
              <div class="api-method post">POST</div>
              <code class="api-url">/api/login</code>
              <p class="api-desc">登录并刷新 Cookies</p>
              <div class="api-examples">
                <h4>请求体:</h4>
                <pre>{
  "email": "your@email.com",
  "password": "your_password"
}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 设置 -->
      <div v-if="activeTab === 'settings'" class="panel">
        <div class="panel-header">
          <h2>⚙️ 设置</h2>
          <button @click="testCookies" :disabled="loading" class="btn btn-sm btn-primary">
            🔗 测试连接
          </button>
        </div>

        <div class="settings-content">
          <!-- 自动刷新状态 -->
          <div v-if="hasAccount" class="auto-refresh-status">
            <span class="status-icon">{{ autoRefreshEnabled ? '✅' : '⚠️' }}</span>
            <span class="status-text">
              自动刷新: {{ autoRefreshEnabled ? '已启用' : '未启用' }}
              <span v-if="autoRefreshEnabled" class="status-hint">
                (Cookies 失效时会自动使用保存的账号重新登录)
              </span>
            </span>
          </div>

          <!-- 账号登录区域 -->
          <div class="settings-section">
            <h3>🔑 账号登录 (推荐)</h3>
            <p class="section-desc">使用账号密码自动登录获取 Cookies，Cookies 失效时会自动刷新</p>
            
            <div class="login-form">
              <div class="form-row">
                <div class="form-group">
                  <label>邮箱</label>
                  <input
                    v-model="accountForm.email"
                    type="email"
                    placeholder="your@email.com"
                    class="form-input"
                  />
                </div>
                <div class="form-group">
                  <label>密码</label>
                  <input
                    v-model="accountForm.password"
                    type="password"
                    placeholder="登录密码"
                    class="form-input"
                  />
                </div>
              </div>
              
              <div class="form-actions">
                <button @click="saveAccount" :disabled="saving" class="btn btn-secondary btn-sm">
                  💾 保存账号
                </button>
                <button @click="loginAndRefresh" :disabled="loggingIn" class="btn btn-primary">
                  {{ loggingIn ? '登录中...' : '🔄 登录并刷新 Cookies' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 分割线 -->
          <div class="divider">
            <span>或者手动设置</span>
          </div>

          <!-- 手动 Cookie 设置 -->
          <div class="settings-section">
            <h3>📋 手动设置 Cookies</h3>
            <div class="settings-info">
              <p>如果自动登录失败，可以手动复制 Cookies：</p>
              <ol>
                <li>在浏览器中打开 <a href="https://smstome.com" target="_blank">smstome.com</a> 并登录</li>
                <li>按 F12 打开开发者工具</li>
                <li>切换到 "Application" → Cookies → smstome.com</li>
                <li>复制 <code>smstome_session</code> 的值</li>
              </ol>
            </div>

            <div class="cookie-form">
              <div class="form-group">
                <label>smstome_session</label>
                <textarea
                  v-model="cookieForm.smstome_session"
                  placeholder="粘贴 smstome_session 的值"
                  class="form-input form-textarea"
                  rows="2"
                ></textarea>
              </div>

              <div class="form-group">
                <label>或者粘贴完整 Cookie 字符串</label>
                <textarea
                  v-model="cookieForm.cookie_string"
                  placeholder="格式: smstome_session=xxx; XSRF-TOKEN=xxx"
                  class="form-input form-textarea"
                  rows="2"
                ></textarea>
              </div>

              <div class="form-actions">
                <button @click="saveCookies" :disabled="saving" class="btn btn-secondary">
                  {{ saving ? '保存中...' : '💾 保存 Cookies' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 当前 Cookies 状态 -->
          <div v-if="currentCookies" class="current-cookies">
            <h3>📊 当前 Cookies</h3>
            <div class="cookie-list">
              <div v-for="(value, key) in currentCookies" :key="key" class="cookie-item">
                <span class="cookie-key">{{ key }}</span>
                <span class="cookie-value">{{ value }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 消息提示 -->
    <div v-if="message" :class="['toast', message.type]" @click="message = null">
      {{ message.type === 'success' ? '✅' : '❌' }} {{ message.text }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'

const API_BASE = 'http://localhost:5001/api'

// 状态
const loading = ref(false)
const loadingSMS = ref(false)
const saving = ref(false)
const message = ref(null)
const activeTab = ref('list')
const isConnected = ref(false)

// 国家 (网站实际支持的列表)
const countries = ref({
  uk: 'united-kingdom',
  poland: 'poland',
  netherlands: 'netherlands',
  sweden: 'sweden',
  finland: 'finland',
  belgium: 'belgium',
  slovenia: 'slovenia'
})

const countryNames = {
  uk: '🇬🇧 英国',
  poland: '🇵🇱 波兰',
  netherlands: '🇳🇱 荷兰',
  sweden: '🇸🇪 瑞典',
  finland: '🇫🇮 芬兰',
  belgium: '🇧🇪 比利时',
  slovenia: '🇸🇮 斯洛文尼亚'
}

const selectedCountry = ref('united-kingdom')
const searchPhone = ref('')

// 手机号列表
const phones = ref([])
const currentPage = ref(1)
const hasMore = ref(true)

// 短信详情
const currentPhoneDetail = ref(null)

// Cookie 设置
const cookieForm = ref({
  cf_clearance: '',
  smstome_session: '',
  cookie_string: ''
})
const currentCookies = ref(null)

// 账号设置
const accountForm = ref({
  email: '',
  password: ''
})
const loggingIn = ref(false)
const autoRefreshEnabled = ref(false)
const hasAccount = ref(false)

// 显示消息
function showMessage(text, type = 'success') {
  message.value = { text, type }
  setTimeout(() => {
    message.value = null
  }, 3000)
}

// 检查连接状态
async function checkConnection() {
  try {
    const resp = await axios.get(`${API_BASE}/health`)
    isConnected.value = resp.data.connected
  } catch {
    isConnected.value = false
  }
}

// 加载手机号列表
async function loadPhones() {
  loading.value = true
  
  try {
    const resp = await axios.get(`${API_BASE}/phones/${selectedCountry.value}`, {
      params: { page: currentPage.value }
    })
    phones.value = resp.data.phones
    hasMore.value = resp.data.has_more
  } catch (e) {
    showMessage(e.response?.data?.error || e.message, 'error')
  } finally {
    loading.value = false
  }
}

// 上一页
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    loadPhones()
  }
}

// 下一页
function nextPage() {
  if (hasMore.value) {
    currentPage.value++
    loadPhones()
  }
}

// 获取当前选中的国家代码
function getCountryCode() {
  return Object.keys(countries.value).find(
    k => countries.value[k] === selectedCountry.value
  ) || 'uk'
}

// 查看手机号短信
async function viewPhoneSMS(phone) {
  loadingSMS.value = true
  activeTab.value = 'sms'
  
  const phoneNum = phone.phone.replace('+', '')
  
  try {
    const resp = await axios.get(`${API_BASE}/phone/${phoneNum}/sms`, {
      params: { country: getCountryCode() }
    })
    currentPhoneDetail.value = resp.data
  } catch (e) {
    showMessage(e.response?.data?.error || e.message, 'error')
  } finally {
    loadingSMS.value = false
  }
}

// 搜索手机号短信
async function searchPhoneSMS() {
  if (!searchPhone.value.trim()) {
    showMessage('请输入手机号', 'error')
    return
  }
  
  loadingSMS.value = true
  activeTab.value = 'sms'
  
  const phoneNum = searchPhone.value.replace('+', '').trim()
  
  try {
    const resp = await axios.get(`${API_BASE}/phone/${phoneNum}/sms`, {
      params: { country: getCountryCode() }
    })
    currentPhoneDetail.value = resp.data
    showMessage(`找到 ${resp.data.sms_count} 条短信`)
  } catch (e) {
    if (e.response?.status === 404) {
      showMessage(`未找到手机号 ${phoneNum}`, 'error')
    } else {
      showMessage(e.response?.data?.error || e.message, 'error')
    }
  } finally {
    loadingSMS.value = false
  }
}

// 加载当前 Cookies
async function loadCookies() {
  try {
    const resp = await axios.get(`${API_BASE}/cookies`)
    currentCookies.value = resp.data.cookies
  } catch (e) {
    currentCookies.value = null
  }
  
  // 同时加载账号
  await loadAccount()
}

// 保存 Cookies
async function saveCookies() {
  saving.value = true
  
  try {
    let data = {}
    
    if (cookieForm.value.cookie_string.trim()) {
      data = { cookie_string: cookieForm.value.cookie_string.trim() }
    } else {
      if (cookieForm.value.cf_clearance.trim()) {
        data.cf_clearance = cookieForm.value.cf_clearance.trim()
      }
      if (cookieForm.value.smstome_session.trim()) {
        data.smstome_session = cookieForm.value.smstome_session.trim()
      }
    }
    
    if (Object.keys(data).length === 0) {
      showMessage('请填写 Cookie 信息', 'error')
      return
    }
    
    const resp = await axios.post(`${API_BASE}/cookies`, data)
    
    if (resp.data.success) {
      showMessage('Cookies 保存成功！' + (resp.data.connected ? ' 连接正常' : ' 但连接失败'))
      isConnected.value = resp.data.connected
      await loadCookies()
      
      // 清空表单
      cookieForm.value = { cf_clearance: '', smstome_session: '', cookie_string: '' }
    }
  } catch (e) {
    showMessage(e.response?.data?.error || e.message, 'error')
  } finally {
    saving.value = false
  }
}

// 测试 Cookies
async function testCookies() {
  loading.value = true
  
  try {
    const resp = await axios.get(`${API_BASE}/cookies/test`)
    isConnected.value = resp.data.connected
    showMessage(resp.data.message, resp.data.connected ? 'success' : 'error')
  } catch (e) {
    showMessage(e.response?.data?.error || '连接失败', 'error')
    isConnected.value = false
  } finally {
    loading.value = false
  }
}

// 加载保存的账号
async function loadAccount() {
  try {
    const resp = await axios.get(`${API_BASE}/account`)
    if (resp.data.email) {
      accountForm.value.email = resp.data.email
      accountForm.value.password = resp.data.password || ''
    }
    autoRefreshEnabled.value = resp.data.auto_refresh_enabled || false
    hasAccount.value = resp.data.has_account || false
  } catch {
    // 忽略错误
  }
}

// 保存账号
async function saveAccount() {
  if (!accountForm.value.email.trim()) {
    showMessage('请输入邮箱', 'error')
    return
  }
  
  saving.value = true
  
  try {
    await axios.post(`${API_BASE}/account`, {
      email: accountForm.value.email.trim(),
      password: accountForm.value.password
    })
    showMessage('账号已保存')
  } catch (e) {
    showMessage(e.response?.data?.error || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 登录并刷新 Cookies
async function loginAndRefresh() {
  if (!accountForm.value.email.trim() || !accountForm.value.password.trim()) {
    showMessage('请输入邮箱和密码', 'error')
    return
  }
  
  loggingIn.value = true
  
  try {
    const resp = await axios.post(`${API_BASE}/login`, {
      email: accountForm.value.email.trim(),
      password: accountForm.value.password
    })
    
    if (resp.data.success) {
      showMessage(resp.data.message)
      isConnected.value = resp.data.connected
      await loadCookies()
      
      // 同时保存账号
      await saveAccount()
    }
  } catch (e) {
    showMessage(e.response?.data?.error || '登录失败', 'error')
    isConnected.value = false
  } finally {
    loggingIn.value = false
  }
}

// 监听国家变化
watch(selectedCountry, () => {
  currentPage.value = 1
  loadPhones()
})

// 初始化
onMounted(() => {
  checkConnection()
  loadPhones()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  color: white;
  padding: 30px 0;
  position: relative;
}

.header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.header p {
  opacity: 0.9;
}

.connection-status {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.connection-status.connected {
  background: rgba(40, 167, 69, 0.9);
}

.connection-status.disconnected {
  background: rgba(220, 53, 69, 0.9);
}

.main {
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.search-section {
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.search-box {
  display: flex;
  gap: 10px;
  max-width: 800px;
  margin: 0 auto;
}

.country-select {
  padding: 12px 16px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.search-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-sm {
  padding: 8px 16px;
  font-size: 12px;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tabs {
  display: flex;
  border-bottom: 1px solid #e9ecef;
}

.tab {
  flex: 1;
  padding: 16px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 600;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover {
  background: #f8f9fa;
}

.tab.active {
  color: #667eea;
  border-bottom: 3px solid #667eea;
}

.panel {
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.panel-header h2 {
  font-size: 1.25rem;
  color: #333;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-info {
  font-size: 14px;
  color: #6c757d;
}

.phone-meta {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #6c757d;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #6c757d;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #adb5bd;
}

.phone-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
}

.phone-card {
  padding: 16px;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.phone-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.phone-number {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  margin-right: 8px;
}

.badge.new {
  background: #28a745;
  color: white;
}

.phone-info {
  font-size: 13px;
  color: #6c757d;
}

.sms-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.sms-card {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
  border-left: 4px solid #667eea;
}

.sms-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
}

.sender {
  font-weight: 600;
  color: #333;
}

.time {
  color: #6c757d;
}

.sms-content {
  font-size: 14px;
  line-height: 1.6;
  color: #495057;
  word-break: break-word;
}

/* 设置页面样式 */
.settings-content {
  max-width: 700px;
}

.settings-section {
  margin-bottom: 24px;
}

.settings-section h3 {
  font-size: 16px;
  color: #333;
  margin-bottom: 8px;
}

.section-desc {
  font-size: 13px;
  color: #6c757d;
  margin-bottom: 16px;
}

.login-form {
  background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
  border: 2px solid #667eea30;
  border-radius: 12px;
  padding: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.divider {
  display: flex;
  align-items: center;
  margin: 32px 0;
  color: #adb5bd;
  font-size: 13px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e9ecef;
}

.divider span {
  padding: 0 16px;
}

.auto-refresh-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #28a74520 0%, #20c99720 100%);
  border: 1px solid #28a74540;
  border-radius: 8px;
  margin-bottom: 20px;
}

.status-icon {
  font-size: 18px;
}

.status-text {
  font-size: 14px;
  color: #333;
}

.status-hint {
  color: #6c757d;
  font-size: 12px;
}

.settings-info {
  background: #e7f3ff;
  border: 1px solid #b6d4fe;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.settings-info p {
  margin-bottom: 12px;
  color: #0c5460;
}

.settings-info ol {
  margin-left: 20px;
  color: #0c5460;
}

.settings-info li {
  margin-bottom: 6px;
}

.settings-info a {
  color: #667eea;
}

.settings-info code {
  background: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.cookie-form {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 12px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  font-family: monospace;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-actions {
  margin-top: 20px;
}

.current-cookies {
  margin-top: 24px;
}

.current-cookies h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: #333;
}

.cookie-list {
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
}

.cookie-item {
  display: flex;
  padding: 12px 16px;
  border-bottom: 1px solid #e9ecef;
}

.cookie-item:last-child {
  border-bottom: none;
}

.cookie-key {
  font-weight: 600;
  min-width: 150px;
  color: #333;
}

.cookie-value {
  font-family: monospace;
  color: #6c757d;
  word-break: break-all;
}

/* 消息提示 */
.toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 16px 24px;
  border-radius: 8px;
  cursor: pointer;
  animation: slideUp 0.3s ease;
  z-index: 1000;
  color: white;
  font-weight: 500;
}

.toast.success {
  background: #28a745;
}

.toast.error {
  background: #dc3545;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@media (max-width: 640px) {
  .search-box {
    flex-direction: column;
  }
  
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .phone-meta {
    flex-direction: column;
    gap: 5px;
  }
  
  .connection-status {
    position: static;
    margin-top: 10px;
  }
}

/* API 文档样式 */
.api-base {
  font-size: 13px;
  color: #6c757d;
}

.api-base code {
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
}

.api-docs {
  max-width: 900px;
}

.api-section {
  margin-bottom: 32px;
}

.api-section h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #667eea;
}

.api-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.api-method {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  margin-right: 8px;
  margin-bottom: 8px;
}

.api-method.get {
  background: #28a745;
  color: white;
}

.api-method.post {
  background: #007bff;
  color: white;
}

.api-method.delete {
  background: #dc3545;
  color: white;
}

.api-url {
  display: inline-block;
  background: #333;
  color: #f8f9fa;
  padding: 6px 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
  margin-bottom: 8px;
}

.api-desc {
  color: #495057;
  margin: 8px 0;
  font-size: 14px;
}

.api-params {
  margin-top: 12px;
}

.api-params h4,
.api-examples h4 {
  font-size: 13px;
  color: #6c757d;
  margin-bottom: 8px;
}

.api-params ul {
  margin: 0;
  padding-left: 20px;
}

.api-params li {
  font-size: 13px;
  color: #495057;
  margin-bottom: 4px;
}

.api-params code {
  background: #e9ecef;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  color: #d63384;
}

.api-examples {
  margin-top: 12px;
}

.api-examples pre {
  background: #2d3748;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 13px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
