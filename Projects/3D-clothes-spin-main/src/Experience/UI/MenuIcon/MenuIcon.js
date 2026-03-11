import * as THREE from 'three';
import Experience from '../../Experience.js';
import "./style.css";

export default class MenuIcon {
    constructor() {
        this.experience = new Experience();
        this.camera = this.experience.camera.instance;
        this.isCameraMoving = () => this.experience.camera.isCameraMoving();
        this.createMenu();
        this.generateMenuIcon();
    }
    createMenu(){
        this.whiteOverlay = document.createElement('div');
        this.whiteOverlay.className = 'white-overlay';
        this.whiteOverlay.id = 'whiteOverlay';
        document.body.appendChild(this.whiteOverlay);

        this.menuIcon = document.createElement('div');
        this.menuIcon.className = 'menu-icon';
        document.body.appendChild(this.menuIcon);

        this.menuIcon.addEventListener('click', this.toggleWhiteOverlay.bind(this));
    }
    generateMenuIcon() {
        for (let i = 0; i < 3; i++) {
            const line = document.createElement('div');
            line.classList.add('menu-icon-line');
            this.menuIcon.appendChild(line);
        }
    }

    toggleWhiteOverlay() {
        this.whiteOverlay.classList.toggle('show');
    }

    update() {
        if (this.isCameraMoving()) {
            this.whiteOverlay.classList.remove('show'); // Remove 'show' class
            this.whiteOverlay.classList.add('notshow'); // Add 'notshow' class
        } else {
            this.whiteOverlay.classList.remove('notshow'); // Remove 'notshow' class
        }
    }
}

