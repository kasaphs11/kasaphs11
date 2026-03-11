import * as THREE from 'three';
import Experience from '../../Experience.js';
import "./style.css";

export default class SoundButton {
    constructor() {
        this.initializeIonicons();
        this.setupSoundButton();
        this.isPlaying = false;
        this.audio = new Audio("audio/museum.mp3");
        this.audio.preload = "auto";
    }

    initializeIonicons() {
        const ioniconsModuleScript = document.createElement("script");
        ioniconsModuleScript.type = "module";
        ioniconsModuleScript.src = "https://unpkg.com/ionicons@7.1.0/dist/ionicons/ionicons.esm.js";
        ioniconsModuleScript.defer = true;
        document.head.appendChild(ioniconsModuleScript);

        const ioniconsScript = document.createElement("script");
        ioniconsScript.src = "https://unpkg.com/ionicons@7.1.0/dist/ionicons/ionicons.js";
        ioniconsScript.defer = true;
        document.head.appendChild(ioniconsScript);
    }

    setupSoundButton() {
        const container = document.createElement('div');
        container.className = 'container';
        
        const soundButton = document.createElement('a');
        soundButton.className = 'sound-button';
        
        const ionIcon = document.createElement('ion-icon');
        ionIcon.id = 'music-icon';
        ionIcon.setAttribute('name', 'musical-notes-outline');
        ionIcon.setAttribute('size', 'large');
        
        soundButton.appendChild(ionIcon);
        
        const bordered = document.createElement('div');
        bordered.className = 'bordered';
        
        container.appendChild(soundButton);
        container.appendChild(bordered);
        
        document.body.appendChild(container);
        
        soundButton.addEventListener("click", this.toggleSound.bind(this));
    }

    toggleSound() {
        const soundButton = document.querySelector(".sound-button");
        soundButton.classList.toggle("clicked");

        if (this.isPlaying) {
            this.audio.pause();
        } else {
            this.audio.play();
        }

        this.isPlaying = !this.isPlaying;
    }

    update() {
        
    }
}
