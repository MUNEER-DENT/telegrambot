document.addEventListener('DOMContentLoaded', () => {
  /* -----------------------------------------------
     التمرير السلس عند النقر على روابط القائمة
  ----------------------------------------------- */
  const navLinks = document.querySelectorAll('header nav ul li a');
  navLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const targetId = this.getAttribute('href').substring(1);
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        targetSection.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  /* -----------------------------------------------
     تحريك الأقسام عند ظهورها باستخدام Intersection Observer
  ----------------------------------------------- */
  const animatedElements = document.querySelectorAll('.animate');
  if (window.IntersectionObserver) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });
    animatedElements.forEach(el => observer.observe(el));
  }

  /* -----------------------------------------------
     معالجة نموذج "تواصل معنا" مع التحقق من صحة البيانات
  ----------------------------------------------- */
  const contactForm = document.getElementById('contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const nameInput = document.getElementById('name');
      const emailInput = document.getElementById('email');
      const messageInput = document.getElementById('message');

      const name = nameInput.value.trim();
      const email = emailInput.value.trim();
      const message = messageInput.value.trim();

      // التحقق من ملء جميع الحقول
      if (name === '' || email === '' || message === '') {
        showModal('يرجى ملء جميع الحقول');
        return;
      }

      // التحقق من صحة البريد الإلكتروني (نمط بسيط)
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailPattern.test(email)) {
        showModal('يرجى إدخال بريد إلكتروني صالح');
        return;
      }

      // هنا يمكنك استخدام fetch أو AJAX لإرسال البيانات إلى الخادم
      // سنقوم بمحاكاة الإرسال وعرض رسالة تأكيد للمستخدم
      showModal('شكراً لتواصلك معنا، سيتم الرد عليك قريباً.');
      contactForm.reset();
    });
  }

  /* -----------------------------------------------
     دالة عرض النافذة (المودال) المخصصة للرسائل
  ----------------------------------------------- */
  function showModal(message) {
    let modal = document.getElementById('custom-modal');
    if (!modal) {
      // إنشاء المودال إذا لم يكن موجوداً
      modal = document.createElement('div');
      modal.id = 'custom-modal';
      modal.innerHTML = `
        <div class="modal-overlay">
          <div class="modal-content">
            <span class="modal-close">&times;</span>
            <p>${message}</p>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
      // إضافة مستمع للإغلاق عند الضغط على زر الإغلاق
      modal.querySelector('.modal-close').addEventListener('click', () => {
        modal.style.display = 'none';
      });
      // إغلاق المودال عند الضغط خارج محتوى النافذة
      window.addEventListener('click', (event) => {
        if (event.target === modal) {
          modal.style.display = 'none';
        }
      });
    } else {
      // تحديث الرسالة إذا كان المودال موجوداً
      modal.querySelector('.modal-content p').textContent = message;
    }
    modal.style.display = 'block';
  }

  /* -----------------------------------------------
     قائمة التنقل للأجهزة المحمولة (Toggle)
  ----------------------------------------------- */
  const menuToggle = document.querySelector('.menu-toggle');
  const navUl = document.querySelector('header nav ul');
  if (menuToggle && navUl) {
    menuToggle.addEventListener('click', () => {
      navUl.classList.toggle('open');
    });
  }

  /* -----------------------------------------------
     تكامل مع Telegram Web App
  ----------------------------------------------- */
  if (window.Telegram && Telegram.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
    console.log("Telegram WebApp is ready");
    // يمكنك استخدام Telegram.WebApp.themeParams لتعديل الثيم حسب احتياجاتك
  }

  /* -----------------------------------------------
     إزالة تأثير التحميل (Preloader) إن وجد
  ----------------------------------------------- */
  const preloader = document.getElementById('preloader');
  if (preloader) {
    preloader.style.display = 'none';
  }
});
