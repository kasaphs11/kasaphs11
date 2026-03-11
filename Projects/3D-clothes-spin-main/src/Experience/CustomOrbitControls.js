import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export default class CustomOrbitControls extends OrbitControls {
    constructor(object, domElement) {
        super(object, domElement);

        // Disable right mouse button rotation
        //this.mouseButtons.RIGHT = null;

        // this.enableZoom = false;
        
    
    }
    

}
