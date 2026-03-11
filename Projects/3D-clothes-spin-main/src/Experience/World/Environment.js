import * as THREE from 'three'
import Experience from '../Experience.js'
import * as dat from 'lil-gui'

export default class Environment
{
    constructor()
    {
        this.experience = new Experience()
        this.scene = this.experience.scene
        //this.resources = this.experience.resources
        this.debug = this.experience.debug
        
        // Debug
        if(this.debug.active)
        {
            this.debugFolder = this.debug.ui.addFolder('environment')
        }

        this.setSunLight()
        //this.setInvCube()
        //this.setEnvironmentMap()
    }

    setSunLight() {
        this.sunLight = new THREE.DirectionalLight(0xffffff, 0.8);
        this.sunLight.position.set(10,17,10);
        this.scene.add(this.sunLight);
        
        

        // Debug
        if (this.debug.active) {
            this.debugFolder
                .add(this.sunLight, 'intensity')
                .name('sunLightIntensity')
                .min(0)
                .max(10)
                .step(0.001);
        }
    }
    // setInvCube(){
    //     this.geometry = new THREE.BoxGeometry(41,3,41);
    //     this.material = new THREE.MeshToonMaterial({
    //         //color: 0x00ff00,  // Color of the faces (you can change this to your desired color)
    //         //wireframe: true   // Display the wireframe
    //       });
    //     this.cube = new THREE.Mesh(this.geometry,this.material);
    //     this.cube.position.x = 12.5
    //     this.cube.position.z = 7
    //     this.scene.add(this.cube);

        
    // }

    // setSunLight()
    // {
        
    //     this.sunLight = new THREE.DirectionalLight(0xffffff, 2, 0);
    // //         this.sunLight.castShadow = true;
    // // //         //this.sunLight.shadow.camera.far = 10;
    // // //         //this.sunLight.shadow.mapSize.set(1024, 1024);
    // // //         //this.sunLight.shadow.normalBias = 0.05;
    // //         this.sunLight.angle = 100
    //     this.sunLight.position.set(50, 100, 50);
    //     //this.sunLight.target(8, 10.5, 8);
            
    // // //         // Create a target object for the light
    // //         this.lightTarget = new THREE.Object3D();
    // //         this.lightTarget.position.set(14.1,0,9.18); // Set the initial target position here
    //      this.scene.add(this.sunLight);
          
    //         // Set the light's target
    //         this.sunLight.target = this.lightTarget;
          
    //         this.scene.add(this.sunLight);
    //         this.directionalLightHelper = new THREE.SpotLightHelper(this.sunLight);
    //         this.scene.add(this.directionalLightHelper);
    //         this.sunLight.intensity = 1.4
    //         this.scene.add(this.sunLight.target)
    //         this.sunLight.target.position.x = 0.75
    //         const gui = new dat.GUI()
    //         // gui.add(this.sunLight.position, 'y', - 30, 30, 0.01)
    //         // gui.add(this.sunLight.position, 'x', - 20, 20, 0.01)
    //         // gui.add(this.sunLight.position, 'z', - 20, 20, 0.01)
        
    //     //Debug
    //     if(this.debug.active)
    //     {
    //         this.debugFolder
    //             .add(this.sunLight, 'intensity')
    //             .name('sunLightIntensity')
    //             .min(0)
    //             .max(10)
    //             .step(0.001)
        
    //         this.debugFolder
    //             .add(this.sunLight.position, 'x')
    //             .name('sunLightX')
    //             .min(- 75)
    //             .max(33.5)
    //             .step(0.0001)
            
    //         this.debugFolder
    //             .add(this.sunLight.position, 'y')
    //             .name('sunLightY')
    //             .min(0)
    //             .max(200)
    //             .step(0.0001)
            
    //         this.debugFolder
    //             .add(this.sunLight.position, 'z')
    //             .name('sunLightZ')
    //             .min(- 13.5)
    //             .max(28)
    //             .step(0.0001)
            
            
    //     } //        
    //}




    // setEnvironmentMap()
    // {
    //     this.environmentMap = {}
    //     this.environmentMap.intensity = 4
    //     this.environmentMap.texture = this.resources.items.environmentMapTexture
    //     //this.environmentMap.texture.encoding = THREE.sRGBEncoding
        
    //     this.scene.environment = this.environmentMap.texture
        
    //     this.environmentMap.updateMaterials = () =>
    //     {
    //         this.scene.traverse((child) =>
    //         {
    //             if(child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial)
    //             {
    //                 child.material.envMap = this.environmentMap.texture
    //                 child.material.envMapIntensity = this.environmentMap.intensity
    //                 child.material.needsUpdate = true
    //             }
    //         })
    //     }
    //     this.environmentMap.updateMaterials()

    //     // Debug
    //     if(this.debug.active)
    //     {
    //         this.debugFolder
    //             .add(this.environmentMap, 'intensity')
    //             .name('envMapIntensity')
    //             .min(0)
    //             .max(10)
    //             .step(0.001)
    //             .onChange(this.environmentMap.updateMaterials)
    //     }
    // } 

    update(){
        
    }
}