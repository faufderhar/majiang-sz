/**
 * Service Worker — 离线缓存支持
 * 
 * PWA 的核心组件之一。Service Worker 运行在浏览器后台，可以：
 * 1. 拦截网络请求并提供缓存响应
 * 2. 支持离线使用（缓存核心页面和样式）
 * 3. 实现后台同步（未来扩展）
 * 
 * 缓存策略：
 * - 静态资源（HTML/CSS/JS）：Cache First（缓存优先）
 * - API 请求：Network First（网络优先，断网时用缓存）
 */

const CACHE_NAME = 'mahjong-assistant-v1';

// 需要预缓存的静态资源列表
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/style.css',
    '/app.js',
    '/manifest.json',
];

/**
 * install 事件 —— 首次安装 Service Worker 时触发
 * 在这里预缓存所有静态资源
 */
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())  // 立即激活，不等待旧 SW 终止
    );
});

/**
 * activate 事件 —— Service Worker 激活时触发
 * 在这里清除旧版本的缓存
 */
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(names => {
            return Promise.all(
                names
                    .filter(name => name !== CACHE_NAME)
                    .map(name => caches.delete(name))
            );
        }).then(() => self.clients.claim())  // 立即接管所有页面
    );
});

/**
 * fetch 事件 —— 拦截所有网络请求
 * 
 * 策略：
 * - API 请求（/api/）：网络优先，失败时返回缓存
 * - 静态资源：缓存优先，没有缓存则从网络获取并缓存
 */
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    // API 请求：Network First
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
        return;
    }
    
    // 静态资源：Cache First
    event.respondWith(
        caches.match(event.request)
            .then(cached => {
                if (cached) return cached;
                return fetch(event.request).then(response => {
                    // 缓存新获取的资源
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => cache.put(event.request, clone));
                    }
                    return response;
                });
            })
    );
});
