import * as THREE from 'three';
import Debug from './Utils/Debug.js';
import MouseListener from './Utils/MouseListener.js';
import OpacityManager from './Utils/OpacityManager.js';
import CenterButton from './UI/CenterButton/CenterButton.js';
import MenuIcon from './UI/MenuIcon/MenuIcon.js';
import SoundButton from './UI/SoundButton/SoundButton.js';
import Sizes from './Utils/Sizes.js';
import Time from './Utils/Time.js';
import Camera from './Camera.js';
import Renderer from './Renderer.js';
import World from './World/World.js';
import Resources from './Utils/Resources.js';
import sources from './sources.js';

let instance = null;

export default class Experience {
    constructor(_canvas) {
        // Singleton
        if (instance) {
            return instance;
        }
        instance = this;

        // Global access
        window.experience = this;

        // Options
        this.canvas = _canvas;

        // Setup
        this.debug = new Debug();
        this.sizes = new Sizes();
        this.time = new Time();
        this.scene = new THREE.Scene();
        this.resources = new Resources(sources);
        this.camera = new Camera();
        this.renderer = new Renderer();
        this.world = new World(this.scene, this.resources, this.camera);
        this.opacityManager = new OpacityManager();
        this.mouseListener = new MouseListener();
        this.centerButton = new CenterButton();
        this.menuIcon = new MenuIcon();
        this.soundButton = new SoundButton();
        
        

        // Resize event
        this.sizes.on('resize', () => {
            this.resize();
        });

        // Time tick event
        this.time.on('tick', () => {
            this.update();
        });

        // Start the rendering loop
        this.startRenderingLoop();
    }

    resize() {
        this.camera.resize();
        this.renderer.resize();
    }

    startRenderingLoop() {
        const render = () => {
            this.update();
            this.renderer.update();
            requestAnimationFrame(render);
        };
        render();
    }

    update() {
        this.camera.update();
        this.world.update();
        this.mouseListener.update();
        this.opacityManager.update();
        this.centerButton.update();
        this.menuIcon.update();
    }

    destroy() {
        this.sizes.off('resize');
        this.time.off('tick');

        // Traverse the whole scene
        this.scene.traverse((child) => {
            // Test if it's a mesh
            if (child instanceof THREE.Mesh) {
                child.geometry.dispose();

                // Loop through the material properties
                for (const key in child.material) {
                    const value = child.material[key];

                    // Test if there is a dispose function
                    if (value && typeof value.dispose === 'function') {
                        value.dispose();
                    }
                }
            }
        });

        this.camera.controls.dispose();
        this.renderer.instance.dispose();

        if (this.debug.active) {
            this.debug.ui.destroy();
        }
    }
}
