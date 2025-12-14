// سیستم Debug و Logging
// این فایل برای ردیابی خطاها و مشکلات استفاده می‌شود

// تنظیمات Debug
const DEBUG_CONFIG = {
    enabled: true, // فعال/غیرفعال کردن debug
    showInConsole: true, // نمایش در console
    showInUI: true, // نمایش در UI
    logLevel: 'all' // 'all', 'error', 'warn', 'info'
};

// ذخیره لاگ‌ها
let debugLogs = [];
const MAX_LOGS = 100;

// تابع اصلی برای لاگ کردن
function debugLog(level, category, message, data = null) {
    if (!DEBUG_CONFIG.enabled) return;
    
    const timestamp = new Date().toLocaleTimeString('fa-IR');
    const logEntry = {
        timestamp,
        level,
        category,
        message,
        data,
        stack: level === 'error' ? new Error().stack : null
    };
    
    // اضافه کردن به آرایه لاگ‌ها
    debugLogs.push(logEntry);
    if (debugLogs.length > MAX_LOGS) {
        debugLogs.shift(); // حذف قدیمی‌ترین لاگ
    }
    
    // نمایش در console
    if (DEBUG_CONFIG.showInConsole) {
        const emoji = {
            'error': '❌',
            'warn': '⚠️',
            'info': 'ℹ️',
            'success': '✅',
            'debug': '🔍'
        }[level] || '📝';
        
        const style = {
            'error': 'color: red; font-weight: bold;',
            'warn': 'color: orange; font-weight: bold;',
            'info': 'color: blue;',
            'success': 'color: green;',
            'debug': 'color: gray;'
        }[level] || '';
        
        console.log(
            `%c${emoji} [${timestamp}] [${category}] ${message}`,
            style,
            data || ''
        );
        
        if (level === 'error' && logEntry.stack) {
            console.error('Stack trace:', logEntry.stack);
        }
    }
    
    // نمایش در UI
    if (DEBUG_CONFIG.showInUI) {
        updateDebugPanel();
    }
}

// توابع راحت برای استفاده
const debug = {
    error: (category, message, data) => debugLog('error', category, message, data),
    warn: (category, message, data) => debugLog('warn', category, message, data),
    info: (category, message, data) => debugLog('info', category, message, data),
    success: (category, message, data) => debugLog('success', category, message, data),
    log: (category, message, data) => debugLog('debug', category, message, data)
};

// ایجاد پنل Debug در UI
function createDebugPanel() {
    if (!DEBUG_CONFIG.showInUI) return;
    
    const panel = document.createElement('div');
    panel.id = 'debug-panel';
    panel.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 400px;
        max-height: 500px;
        background: rgba(0, 0, 0, 0.9);
        color: #fff;
        border: 2px solid #ff4444;
        border-radius: 8px;
        padding: 10px;
        font-family: monospace;
        font-size: 12px;
        z-index: 99999;
        overflow-y: auto;
        display: none;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    `;
    
    const header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #444;';
    
    const title = document.createElement('div');
    title.textContent = '🐛 Debug Panel';
    title.style.cssText = 'font-weight: bold; color: #ff4444;';
    
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = 'background: #ff4444; color: white; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer;';
    closeBtn.onclick = () => panel.style.display = 'none';
    
    const toggleBtn = document.createElement('button');
    toggleBtn.textContent = 'Clear';
    toggleBtn.style.cssText = 'background: #444; color: white; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer; margin-left: 5px;';
    toggleBtn.onclick = () => {
        debugLogs = [];
        updateDebugPanel();
    };
    
    header.appendChild(title);
    header.appendChild(document.createElement('div')).appendChild(closeBtn);
    header.lastChild.appendChild(toggleBtn);
    
    const content = document.createElement('div');
    content.id = 'debug-panel-content';
    content.style.cssText = 'max-height: 400px; overflow-y: auto;';
    
    panel.appendChild(header);
    panel.appendChild(content);
    
    document.body.appendChild(panel);
    
    // دکمه toggle برای نمایش/مخفی کردن پنل
    const toggleButton = document.createElement('button');
    toggleButton.textContent = '🐛';
    toggleButton.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 50px;
        height: 50px;
        background: #ff4444;
        color: white;
        border: none;
        border-radius: 50%;
        font-size: 20px;
        cursor: pointer;
        z-index: 99998;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    `;
    toggleButton.onclick = () => {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    };
    document.body.appendChild(toggleButton);
}

// به‌روزرسانی پنل Debug
function updateDebugPanel() {
    if (!DEBUG_CONFIG.showInUI) return;
    
    const content = document.getElementById('debug-panel-content');
    if (!content) return;
    
    // نمایش فقط آخرین 50 لاگ
    const recentLogs = debugLogs.slice(-50).reverse();
    
    content.innerHTML = recentLogs.map(log => {
        const color = {
            'error': '#ff4444',
            'warn': '#ffaa00',
            'info': '#4488ff',
            'success': '#44ff44',
            'debug': '#888888'
        }[log.level] || '#ffffff';
        
        return `
            <div style="margin-bottom: 8px; padding: 5px; border-left: 3px solid ${color}; background: rgba(255,255,255,0.05);">
                <div style="color: ${color}; font-weight: bold;">
                    [${log.timestamp}] [${log.category}] ${log.message}
                </div>
                ${log.data ? `<div style="color: #aaa; margin-top: 5px; font-size: 10px;">${JSON.stringify(log.data, null, 2)}</div>` : ''}
            </div>
        `;
    }).join('');
    
    // اسکرول به پایین
    content.scrollTop = content.scrollHeight;
}

// اضافه کردن error handler برای خطاهای catch نشده
window.addEventListener('error', (event) => {
    debug.error('Global Error', event.message, {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
    });
});

// اضافه کردن handler برای Promise rejections
window.addEventListener('unhandledrejection', (event) => {
    debug.error('Unhandled Promise Rejection', event.reason?.message || 'Unknown error', {
        reason: event.reason
    });
});

// اضافه کردن debug به توابع مهم
function wrapFunctionWithDebug(originalFunction, functionName, category) {
    return function(...args) {
        debug.log(category, `Calling ${functionName}`, { args });
        try {
            const result = originalFunction.apply(this, args);
            if (result instanceof Promise) {
                return result
                    .then(data => {
                        debug.success(category, `${functionName} succeeded`, { result: data });
                        return data;
                    })
                    .catch(error => {
                        debug.error(category, `${functionName} failed`, { error: error.message, stack: error.stack });
                        throw error;
                    });
            } else {
                debug.success(category, `${functionName} completed`, { result });
                return result;
            }
        } catch (error) {
            debug.error(category, `${functionName} threw error`, { error: error.message, stack: error.stack });
            throw error;
        }
    };
}

// راه‌اندازی پنل Debug هنگام بارگذاری صفحه
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createDebugPanel);
    } else {
        createDebugPanel();
    }
}

// Export برای استفاده در فایل‌های دیگر
if (typeof window !== 'undefined') {
    window.debug = debug;
    window.debugLogs = debugLogs;
    window.getDebugLogs = () => debugLogs;
    window.clearDebugLogs = () => { debugLogs = []; updateDebugPanel(); };
}

// لاگ اولیه
debug.info('Debug System', 'Debug system initialized', { config: DEBUG_CONFIG });

