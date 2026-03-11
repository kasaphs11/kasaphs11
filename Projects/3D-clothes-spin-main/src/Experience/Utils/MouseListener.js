// Import the necessary libraries and modules
import * as THREE from 'three';
import Experience from '../Experience.js';

export default class MouseListener {
    constructor() {
      
        // Initialize the experience and camera
        this.experience = new Experience();
        this.camera = this.experience.camera.instance;
        // Initialize variables
        this.initListeners();
        this.ClickedForPlus = 0;
        this.lastClickedCostumeID = null;

        // Check if the camera is currently moving
        this.isCameraMoving = () => this.experience.camera.isCameraMoving();
        
    }

    // Set the array of costume objects
    setCostumes(costumeArray) {
        this.costumeArray = costumeArray;
    }

    // Get the number of times clicked for a plus
    getClickedForPlus() {
        return this.ClickedForPlus;
    }

    // Set up raycasting for mouse interaction
    setRaycast() {
        const mouse = new THREE.Vector2(
            (event.clientX / window.innerWidth) * 2 - 1,
            -(event.clientY / window.innerHeight) * 2 + 1
        );
        this.raycaster = new THREE.Raycaster();
        this.raycaster.setFromCamera(mouse, this.camera);
        this.intersects = this.raycaster.intersectObjects(this.costumeArray.map((costume) => costume.mesh));
    }

    // Check the alpha value of a pixel on a texture
    setAlphaCheck(index, intersectObject) {
        const pixelCoordinates = this.intersects[index].uv;
        const canvasCopy = document.createElement('canvas');
        canvasCopy.width = intersectObject.material.map.image.width;
        canvasCopy.height = intersectObject.material.map.image.height;
        const contextCopy = canvasCopy.getContext('2d');
        contextCopy.drawImage(intersectObject.material.map.image, 0, 0);
        const xCoord = Math.floor(pixelCoordinates.x * canvasCopy.width);
        const yCoord = Math.floor((1 - pixelCoordinates.y) * canvasCopy.height);
        const pixelData = contextCopy.getImageData(xCoord, yCoord, 1, 1).data;
        return pixelData[3];
    }

    setCameraFocus(position, vector){
        this.experience.camera.setFocusArea(position, vector.x, vector.y, vector.z);
        this.ClickedForPlus += 1;
    }

    // Initialize mouse event listeners
    initListeners() {
        // Mouse down event
        document.addEventListener('mousedown', (event) => {
            this.setRaycast();
            if (this.isCameraMoving()) {
                return;
            }
            if (this.intersects.length > 0 && event.button === 0) {
                // Get the closest intersected object (costume)
                this.intersectedObject = this.intersects[0].object;
                // Get the ID of the clicked costume
                this.storeCostumeID = this.intersectedObject.userData.id;
                const alphaValue = this.setAlphaCheck(0, this.intersectedObject);
                this.AlphaMouseUp = alphaValue === 0 ? 0 : 1;
            } else {
                this.storeCostumeID = null;
            }
        });

        // Mouse up event
        document.addEventListener('mouseup', (event) => {
            this.setRaycast();
            if (this.isCameraMoving()) {
                return;
            }
            if (this.intersects.length > 0 && event.button === 0) {
                // Get the closest intersected object (costume)
                this.intersectedObject = this.intersects[0].object;
                // Get the ID of the clicked costume
                this.clickedCostumeID = this.intersectedObject.userData.id;
                // Get the target position for the clicked costume
                const clickedCostume = this.costumeArray.find((costume) => costume.mesh.userData.id === this.clickedCostumeID);
                const alphaValue = this.setAlphaCheck(0, this.intersectedObject);
                this.AlphaMouseDown = alphaValue === 0 ? 0 : 1;

                if (clickedCostume && this.clickedCostumeID == this.storeCostumeID && this.AlphaMouseUp == this.AlphaMouseDown) {
                    for (let i = 0; i < this.intersects.length; i++) {
                        if (alphaValue > 0) {
                                if (this.lastClickedCostumeID !== this.clickedCostumeID) {
                                    // Set the focus area of the camera to the position of the clicked costume
                                    this.setCameraFocus(clickedCostume.mesh.position, this.clickedCostumeID);
                                    this.lastClickedCostumeID = this.clickedCostumeID;   
                                }
                        } else if (alphaValue == 0 && this.intersects.length > 1) {
                            this.intersectsBehind = this.raycaster.intersectObjects(this.costumeArray.map((costume) => costume.mesh));
                            const behindObject = this.intersectsBehind[i].object;
                            const behindAlphaValue = this.setAlphaCheck(i, behindObject);
                            if (behindAlphaValue > 0 ) {
                                // Set the focus area of the camera to the position of the behind clicked costume
                                this.setCameraFocus(behindObject.position, behindObject.userData.id);
                                this.lastClickedCostumeID = behindObject.userData.id;
                            }
                        }
                    } 
                }
            }
        });
    }
    
    // updatecenterbuttoninfo(){
    //     this.clickedCostumeID 
    //     //find costume class from id
    //     //update centerbutton giving costume.info

    // }
    
    update() {

    }
}


