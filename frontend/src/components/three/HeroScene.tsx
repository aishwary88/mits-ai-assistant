import { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * 3D hero scene: central AI core with connected neural nodes,
 * floating knowledge particles, and glass-like layered elements.
 *
 * Performance:
 *   - Lazy-loaded by the parent via React.lazy.
 *   - Pixel ratio capped at 2.
 *   - Render loop paused when off-screen (IntersectionObserver) or tab hidden.
 *   - All geometries/materials disposed on unmount.
 *   - Honours prefers-reduced-motion (static scene, no parallax).
 */

export default function HeroScene() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;

    // --- Scene & camera ---
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      50,
      container.clientWidth / Math.max(container.clientHeight, 1),
      0.1,
      100,
    );
    camera.position.set(0, 0, 6);

    // --- Renderer ---
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // --- Lights ---
    scene.add(new THREE.AmbientLight(0x174a8b, 0.4));

    const blueLight = new THREE.PointLight(0x2463a6, 1.2, 15);
    blueLight.position.set(3, 2, 4);
    scene.add(blueLight);

    const goldLight = new THREE.PointLight(0xe5b548, 0.6, 12);
    goldLight.position.set(-3, -2, 3);
    scene.add(goldLight);

    // --- Central core (icosahedron + wireframe) ---
    const coreGroup = new THREE.Group();

    const coreGeo = new THREE.IcosahedronGeometry(1.2, 1);
    const coreMat = new THREE.MeshPhongMaterial({
      color: 0x174a8b,
      emissive: 0x0a2540,
      transparent: true,
      opacity: 0.12,
      shininess: 80,
    });
    coreGroup.add(new THREE.Mesh(coreGeo, coreMat));

    const wireGeo = new THREE.IcosahedronGeometry(1.3, 1);
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x2463a6,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    coreGroup.add(wireMesh);

    // Inner glow sphere
    const glowGeo = new THREE.IcosahedronGeometry(0.7, 0);
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0xe5b548,
      transparent: true,
      opacity: 0.06,
    });
    coreGroup.add(new THREE.Mesh(glowGeo, glowMat));

    scene.add(coreGroup);

    // --- Neural nodes ---
    const NODE_COUNT = 6;
    const nodes: THREE.Mesh[] = [];
    const lines: THREE.Line[] = [];

    for (let i = 0; i < NODE_COUNT; i++) {
      const angle = (i / NODE_COUNT) * Math.PI * 2;
      const radius = 2.4 + Math.random() * 0.4;
      const y = (Math.random() - 0.5) * 1.8;
      const pos = new THREE.Vector3(
        Math.cos(angle) * radius,
        y,
        Math.sin(angle) * radius,
      );

      const nodeGeo = new THREE.SphereGeometry(0.11, 16, 16);
      const isAccent = i % 3 === 0;
      const nodeMat = new THREE.MeshBasicMaterial({
        color: isAccent ? 0xe5b548 : 0x2463a6,
        transparent: true,
        opacity: 0.85,
      });
      const node = new THREE.Mesh(nodeGeo, nodeMat);
      node.position.copy(pos);
      nodes.push(node);
      scene.add(node);

      // Connection line
      const lineGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        pos,
      ]);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x2463a6,
        transparent: true,
        opacity: 0.18,
      });
      const line = new THREE.Line(lineGeo, lineMat);
      lines.push(line);
      scene.add(line);
    }

    // --- Floating particles ---
    const PARTICLE_COUNT = 28;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const velocities: { x: number; y: number; z: number }[] = [];

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 8;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 6;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 4;
      velocities.push({
        x: (Math.random() - 0.5) * 0.004,
        y: (Math.random() - 0.5) * 0.004,
        z: (Math.random() - 0.5) * 0.002,
      });
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x2463a6,
      size: 0.04,
      transparent: true,
      opacity: 0.35,
      sizeAttenuation: true,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // --- Mouse parallax ---
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      targetX = (e.clientX / window.innerWidth - 0.5) * 0.4;
      targetY = (e.clientY / window.innerHeight - 0.5) * 0.4;
    };

    if (!prefersReducedMotion) {
      window.addEventListener('mousemove', handleMouseMove);
    }

    // --- Animation loop ---
    let rafId = 0;

    const animate = () => {
      rafId = requestAnimationFrame(animate);

      if (!prefersReducedMotion) {
        // Smooth mouse follow
        mouseX += (targetX - mouseX) * 0.05;
        mouseY += (targetY - mouseY) * 0.05;
        camera.position.x = mouseX * 1.5;
        camera.position.y = -mouseY * 1.5;
        camera.lookAt(0, 0, 0);

        // Auto-rotate
        coreGroup.rotation.y += 0.003;
        coreGroup.rotation.x += 0.001;
        wireMesh.rotation.y -= 0.002;

        // Animate particles
        const pos = particleGeo.attributes.position.array as Float32Array;
        for (let i = 0; i < PARTICLE_COUNT; i++) {
          pos[i * 3] += velocities[i].x;
          pos[i * 3 + 1] += velocities[i].y;
          pos[i * 3 + 2] += velocities[i].z;
          if (Math.abs(pos[i * 3]) > 4) velocities[i].x *= -1;
          if (Math.abs(pos[i * 3 + 1]) > 3) velocities[i].y *= -1;
          if (Math.abs(pos[i * 3 + 2]) > 2) velocities[i].z *= -1;
        }
        particleGeo.attributes.position.needsUpdate = true;

        // Pulse nodes
        nodes.forEach((node, i) => {
          const scale = 1 + Math.sin(Date.now() * 0.001 + i) * 0.15;
          node.scale.setScalar(scale);
        });
      }

      renderer.render(scene, camera);
    };

    animate();

    // --- Pause when off-screen ---
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !rafId) {
        animate();
      } else if (!entries[0].isIntersecting && rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
    });
    observer.observe(container);

    // --- Pause when tab hidden ---
    const handleVisibility = () => {
      if (document.hidden && rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      } else if (!document.hidden && !rafId) {
        animate();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    // --- Resize ---
    const handleResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / Math.max(container.clientHeight, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    // --- Cleanup ---
    return () => {
      cancelAnimationFrame(rafId);
      rafId = 0;
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('visibilitychange', handleVisibility);
      observer.disconnect();

      coreGeo.dispose();
      coreMat.dispose();
      wireGeo.dispose();
      wireMat.dispose();
      glowGeo.dispose();
      glowMat.dispose();
      nodes.forEach((n) => {
        n.geometry.dispose();
        (n.material as THREE.Material).dispose();
      });
      lines.forEach((l) => {
        l.geometry.dispose();
        (l.material as THREE.Material).dispose();
      });
      particleGeo.dispose();
      particleMat.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div ref={containerRef} className="h-full w-full" />;
}
