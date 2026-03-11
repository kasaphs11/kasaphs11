import * as THREE from 'three';
import Experience from '../Experience.js';



export default class OpacityManager {


    constructor() {

        this.experience = new Experience();
        this.camera = this.experience.camera.instance;
        this.world = experience.world;        

    }

    setCostumes(costumeArray){
        this.costumeArray = costumeArray
    }

    calculateOpacity() {
        for (const costume of this.costumeArray) {
            const costumePosition = costume.mesh.position;
            const distance = Math.sqrt((this.camera.position.x - costumePosition.x) ** 2 + (this.camera.position.z - costumePosition.z) ** 2);
            if (distance < 3.8) {
                if (costume.material.opacity > 0.9) {
                    costume.material.opacity *= 0.99;
                } else if (costume.material.opacity > 0.5) {
                    costume.material.opacity *= 0.99;
                } else if (costume.material.opacity > 0.2) {
                    costume.material.opacity *= 0.99;
                }
            } else if (distance > 3.7) {
                costume.material.opacity = 1;
            } else if (distance > 3 && costume.material.opacity > 0.5 && costume.material.opacity < 0.8) {
                costume.material.opacity *= 1.2;
            } else if (distance > 2 && costume.material.opacity > 0.2 && costume.material.opacity < 0.4) {
                costume.material.opacity *= 1.3;
            }
        }
    }
    update() {  
        if(this.costumeArray == null){
            return;
        }
        this.calculateOpacity(); 
    }

}
