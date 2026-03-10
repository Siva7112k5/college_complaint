// Global variables
let notificationInterval;

// Document ready
$(document).ready(function() {
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Check for new notifications
    if($('#userLoggedIn').val()) {
        startNotificationCheck();
    }
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Form validation
    $('form').on('submit', function(e) {
        let isValid = true;
        $(this).find('[required]').each(function() {
            if(!$(this).val()) {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        if(!isValid) {
            e.preventDefault();
            showAlert('Please fill all required fields', 'danger');
        }
    });
    
    // Search functionality
    $('#searchInput').on('keyup', function() {
        let searchText = $(this).val().toLowerCase();
        $('.searchable-row').each(function() {
            let rowText = $(this).text().toLowerCase();
            $(this).toggle(rowText.indexOf(searchText) > -1);
        });
    });
});

// Show alert
function showAlert(message, type = 'success') {
    let alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3" style="z-index: 9999;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('body').append(alertHtml);
    
    setTimeout(function() {
        $('.alert').fadeOut('slow', function() {
            $(this).remove();
        });
    }, 5000);
}

// Notification functions
function startNotificationCheck() {
    notificationInterval = setInterval(checkNotifications, 30000);
}

function stopNotificationCheck() {
    if(notificationInterval) {
        clearInterval(notificationInterval);
    }
}

function checkNotifications() {
    $.get('/api/notifications/count', function(data) {
        if(data.count > 0) {
            $('#notificationBadge').text(data.count).show();
            playNotificationSound();
        } else {
            $('#notificationBadge').hide();
        }
    });
}

function playNotificationSound() {
    let audio = new Audio('/static/sounds/notification.mp3');
    audio.play().catch(e => console.log('Audio play failed'));
}

// Format date
function formatDate(dateString) {
    let date = new Date(dateString);
    let now = new Date();
    let diff = Math.floor((now - date) / 1000);
    
    if(diff < 60) return 'Just now';
    if(diff < 3600) return Math.floor(diff / 60) + ' minutes ago';
    if(diff < 86400) return Math.floor(diff / 3600) + ' hours ago';
    return date.toLocaleDateString();
}

// Confirm action
function confirmAction(message, callback) {
    if(confirm(message)) {
        callback();
    }
}

// Print
function printElement(elementId) {
    let printContents = document.getElementById(elementId).innerHTML;
    let originalContents = document.body.innerHTML;
    
    document.body.innerHTML = printContents;
    window.print();
    document.body.innerHTML = originalContents;
}

// Toggle sidebar on mobile
$('#sidebarToggle').on('click', function() {
    $('.sidebar').toggleClass('show');
});

// Character counter for textarea
$('textarea').on('input', function() {
    let length = $(this).val().length;
    let maxLength = $(this).attr('maxlength');
    let counter = $(this).siblings('.char-counter');
    
    if(counter.length) {
        counter.text(length + (maxLength ? '/' + maxLength : '') + ' characters');
        if(maxLength && length > maxLength * 0.8) {
            counter.addClass('text-danger');
        } else {
            counter.removeClass('text-danger');
        }
    }
});

// Add to your base.html or custom.js
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.createElement('div');
    
    overlay.className = 'modal-overlay';
    document.body.appendChild(overlay);
    
    menuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('show');
        overlay.classList.toggle('show');
    });
    
    overlay.addEventListener('click', function() {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
    });
});