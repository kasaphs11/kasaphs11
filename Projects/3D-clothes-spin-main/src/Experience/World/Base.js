import * as THREE from 'three'
import Experience from '../Experience.js'

export default class Base
{
    constructor()
    {
        this.experience = new Experience()
        this.scene = this.experience.scene
        this.resources = this.experience.resources
        this.resource = this.resources.items.BaseModel
        
        this.setModel()   
    }

    setModel()
    {
        this.textureLoader = new THREE.TextureLoader();
        this.bakedTexture = this.textureLoader.load(this.bakedTexturePath)
        this.bakedTexture.flipY = false
        const  DiffuseTexture = this.textureLoader.load('models/Plane/Base_Flat.png')
        
        DiffuseTexture.anisotropy = 32;
        DiffuseTexture.flipY = false

        this.model = this.resource.scene
        this.model.scale.set(1.5,1.5,1.5)
        this.model.position.set(0,-1.3,0)

        this.model.traverse((child) => {
            if (child instanceof THREE.Mesh) {
                // Create a custom material that combines the texture with the color
                const customMaterial = new THREE.MeshBasicMaterial({
                map: DiffuseTexture, // Preserve the existing texture
                //normalMap : NormalTexture,
                //reflectivity :0.2,
                //metalnessMap : MettalicTexture,
                //metalness : 1.0,
                //roughness: 0.3,
                //   clearcoat: 1,
                //   wireframe: false, // You can set this to true to display wireframes
                });
                child.material = customMaterial;
                
              }
                
          });
        this.scene.add(this.model)
    }
    
  
}