import * as THREE from 'three';
import Experience from '../Experience.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

export default class Museum {
  constructor() {
    this.experience = new Experience();
    this.scene = this.experience.scene;
    this.resources = this.experience.resources;
    this.bakedTexturePath = 'models/Museum/8k_Bake_light.jpg'
    this.resource = this.resources.items.museumModel;
    this.setModel();
  }

  setModel() {
    
    //Load Baked Object
    this.textureLoader = new THREE.TextureLoader();
    this.bakedTexture = this.textureLoader.load(this.bakedTexturePath)
    this.bakedTexture.flipY = false
    // Nick position:(8,4.8,8)
    // Fillipos position:(8,-1.5,8)
    this.model = this.resource.scene;
    this.model.scale.set(1.5, 1.5, 1.5);
    this.model.position.set(0,-47.8,0)

    // Traverse the model's children and apply custom material to each Mesh instance
    this.model.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        // Create a custom material that combines the texture with the color
        const customMaterial = new THREE.MeshBasicMaterial({
          map: this.bakedTexture, // Preserve the existing texture
           // Set the desired color here
          color: '#eeeeee',
          wireframe: false, // You can set this to true to display wireframes
        });
        
        child.material = customMaterial;
      }
    });

    this.scene.add(this.model);
    
  }
}
