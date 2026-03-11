import * as THREE from 'three';
import Experience from '../../Experience.js';
import "./style.css";

import MouseListener from "../../Utils/MouseListener.js"
export default class CenterButton {
    constructor(costumeID) {
        this.experience = new Experience();
        this.camera = this.experience.camera.instance;
        this.world = this.experience.world;
        this.mouseListener = this.experience.mouseListener;
        this.isCameraMoving = () => this.experience.camera.isCameraMoving();
        this.info= null;
        
        this.createButton();
         
        // this.costumeTexts = [
        //    
        // ];
    }
    
    // updateCostumeInfo(info){
        
    //     this.info = info

    // }


    createButton() {
        //console.log(this.clickedCostumeID);
        this.centerButton = document.createElement('div');
        this.centerButton.className = 'center-button';
        this.centerButton.id = `center_button_${this.clickedCostumeID}`;
        const bar = document.createElement('div');
        bar.className = 'bar';
        this.centerButton.appendChild(bar);
        document.body.appendChild(this.centerButton);

        this.plusOverlay = document.createElement('div');
        this.plusOverlay.className = 'plus-overlay';

        this.plusOverlay.id = `plusOverlay_${this.clickedCostumeID}`; 
        document.body.appendChild(this.plusOverlay);
       
        // const text = document.createElement('div');
        // text.className = 'text';
        // text.textContent = this.costumeTexts[this.costumeID]
        // this.plusOverlay.appendChild(text);
        
        this.centerButton.addEventListener('click', this.togglePlusOverlay.bind(this));
    }

    togglePlusOverlay() {
        const plusOverlay = document.getElementById(`plusOverlay_${this.clickedCostumeID}`);
        plusOverlay.classList.toggle('show');
    }

    setOpacity(opacity) {
        this.centerButton.style.opacity = opacity;
    }

    update() {
        this.ClickedForPlus = this.mouseListener.getClickedForPlus();
        if (this.ClickedForPlus > 0) {
            if (this.isCameraMoving()) {
                this.setOpacity(0);
            } else {
                this.setOpacity(1);
            }
        }
    }
}
