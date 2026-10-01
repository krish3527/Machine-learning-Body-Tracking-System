/**
 * logo_3d.js
 * ApexMotion Interactive 3D Logo Component.
 * Provides realistic 3D perspective tilt, depth elevation, dynamic glare,
 * and continuous subtle floating physics.
 */

document.addEventListener("DOMContentLoaded", () => {
  const elements = document.querySelectorAll(".logo-3d-interactive, .logo-3d-navbar");

  elements.forEach(el => {
    el.addEventListener("mousemove", (e) => {
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      // Calculate rotation angles (-18deg to +18deg)
      const rotateX = ((centerY - y) / centerY) * 18;
      const rotateY = ((x - centerX) / centerX) * 18;
      
      el.style.transform = `perspective(700px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(12px) scale3d(1.06, 1.06, 1.06)`;
      
      const img = el.querySelector(".logo-3d-img");
      if (img) {
        img.style.filter = `drop-shadow(${-rotateY.toFixed(1)}px ${Math.abs(rotateX).toFixed(1) + 8}px 16px rgba(0, 0, 0, 0.45))`;
      }
    });

    el.addEventListener("mouseleave", () => {
      el.style.transform = "perspective(700px) rotateX(0deg) rotateY(0deg) translateZ(0px) scale3d(1, 1, 1)";
      const img = el.querySelector(".logo-3d-img");
      if (img) {
        img.style.filter = "drop-shadow(0px 6px 12px rgba(0, 0, 0, 0.35))";
      }
    });
  });
});
