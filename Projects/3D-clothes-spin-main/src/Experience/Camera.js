import * as THREE from 'three'
import Experience from './Experience.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import CustomOrbitControls from './CustomOrbitControls.js';
import World from './World/World.js'
import TWEEN from '@tweenjs/tween.js'
export default class Camera
{
    constructor()
    {
        this.experience = new Experience()
        this.sizes = this.experience.sizes
        this.scene = this.experience.scene
        this.canvas = this.experience.canvas
        this.position = this.clickedCostume
        this.setInstance()
        this.setControls()
    }

    setInstance()
    {
        this.instance = new THREE.PerspectiveCamera(60, this.sizes.width / this.sizes.height, 0.1, 10000)
        this.instance.position.set(-10, 2, -10)
        
        this.scene.add(this.instance)
    }

    setControls()
    {
        this.controls = new CustomOrbitControls(this.instance, this.canvas)
        this.controls.enableDamping = true
        const verticalRotationAngle =  Math.PI * 0.42
        this.controls.minPolarAngle = verticalRotationAngle
        this.controls.maxPolarAngle = verticalRotationAngle

        // const axesHelper = new THREE.AxesHelper( 5000 );
        // this.scene.add( axesHelper );
         // Zoom
         this.controls.minDistance = 4
         this.controls.maxDistance = 4
    }

    resize()
    {
        this.instance.aspect = this.sizes.width / this.sizes.height
        this.instance.updateProjectionMatrix()
    }
    disableControls() {
      this.controls.enabled = false;
    }

    enableControls() {
        this.controls.enabled = true;
    }
    setFocusArea(position, camerax, cameray, cameraz) {
      // Define the target position for the camera
      const targetPosition = new THREE.Vector3(position.x , position.y, position.z);
      const cameraPosition = new THREE.Vector3(camerax, cameray, cameraz);

      // Calculate the current camera position
      const currentCameraPosition = new THREE.Vector3();
      currentCameraPosition.copy(this.instance.position);
      this.disableControls();
      const onCompleteCallback = () => {
          this.enableControls();
      };
      
      // Animate the zoom
      new TWEEN.Tween(this.controls.target)
          .to(targetPosition, 2500)
          .easing(TWEEN.Easing.Linear.None)
          .onUpdate(() => {
              this.instance.position.x += 2; // You can update the camera position during the animation if needed
          })
          .onComplete(onCompleteCallback)
          .start();

      // Animate the focus
      new TWEEN.Tween(currentCameraPosition)
          .to(cameraPosition, 2500)
          .easing(TWEEN.Easing.Linear.None)
          .onUpdate(() => {
              this.instance.position.copy(currentCameraPosition);
              
          })
          .onComplete(onCompleteCallback)
          .start();
    }

    update(delta) {
        TWEEN.update();
        this.controls.update(delta);
    }
    
    // Check if the camera is currently moving
    isCameraMoving() {
        return TWEEN.getAll().length > 0;
    }
}