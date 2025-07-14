// 主要JavaScript功能

document.addEventListener('DOMContentLoaded', function() {
    // 自动隐藏提示消息
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            if (alert.classList.contains('show')) {
                alert.classList.remove('show');
                alert.classList.add('fade');
                setTimeout(function() {
                    alert.remove();
                }, 150);
            }
        }, 5000);
    });
    
    // 音频播放控制
    const audioElements = document.querySelectorAll('audio');
    audioElements.forEach(function(audio) {
        audio.addEventListener('play', function() {
            // 暂停其他正在播放的音频
            audioElements.forEach(function(otherAudio) {
                if (otherAudio !== audio && !otherAudio.paused) {
                    otherAudio.pause();
                }
            });
        });
    });
    
    // 表单验证增强
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
                
                // 如果表单验证失败，重新启用按钮
                setTimeout(function() {
                    if (!form.checkValidity()) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || '提交';
                    }
                }, 100);
            }
        });
    });
    
    // 保存按钮原始文本
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(function(btn) {
        btn.setAttribute('data-original-text', btn.innerHTML);
    });
});

// 工具函数
function formatCurrency(amount) {
    return '¥' + parseFloat(amount).toFixed(2);
}

function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
}
