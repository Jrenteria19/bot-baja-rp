document.addEventListener('DOMContentLoaded', () => {
    // Menú móvil (Hamburguesa)
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');

    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // Cerrar menú al hacer clic en un enlace (en móvil)
    const navItems = document.querySelectorAll('.nav-links li a');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
            }
        });
    });

    // Cambiar estilo del navbar al hacer scroll
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // Comprobar si el usuario está logueado para actualizar la Navbar
    fetch('/api/user_info')
        .then(res => res.json())
        .then(data => {
            if (data && !data.error && (data.is_verified || data.is_admin)) {
                // El usuario está logueado y verificado (o es admin)
                const navCtas = document.querySelectorAll('.nav-cta');
                navCtas.forEach(btn => {
                    btn.innerHTML = `<img src="${data.avatar_url}" style="width: 25px; height: 25px; border-radius: 50%; vertical-align: middle; margin-right: 8px; border: 1px solid var(--primary-color);"> ${data.discord_name}`;
                    btn.href = "/dashboard.html";
                    btn.style.display = "inline-flex";
                    btn.style.alignItems = "center";
                    btn.style.background = "rgba(255, 255, 255, 0.1)";
                    btn.style.border = "1px solid rgba(255, 255, 255, 0.2)";
                });
            }
        })
        .catch(err => console.error("No se pudo obtener info del usuario", err));
});
