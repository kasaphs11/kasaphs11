import * as THREE from 'three';
import Experience from '../Experience.js';

export default class Costume {
    constructor(path) {
        this.experience = new Experience()
        this.scene = this.experience.scene
        this.camera = this.experience.camera
        this.resources = this.experience.resources
        this.path = path
        this.costumeTextures = [] // array to hold all textures for the 360 spin
        this.createCostume()
    }

    setGeometry() {
        // create a cylinder geometry to map the textures onto
        const width = 2
        const height = 3
        this.geometry = new THREE.PlaneGeometry(width, height);
        
    }

    setTextures() {
        this.name = [
            '/textures/costumes/Golfo/',
            '/textures/costumes/KAdreas/',
            '/textures/costumes/Yvoni/',
            '/textures/costumes/Xotiko/',
            '/textures/costumes/Achilleas/',
            '/textures/costumes/Alonso/',
            '/textures/costumes/donzuan/',
            '/textures/costumes/ermis/',
            '/textures/costumes/Romeo/',
            '/textures/costumes/Sirina/',
            '/textures/costumes/Tiresias/',
            '/textures/costumes/Varonos/',
            '/textures/costumes/Golfo1/',
            '/textures/costumes/KAdreas1/',
            '/textures/costumes/Yvoni1/',
            '/textures/costumes/Xotiko1/',
            '/textures/costumes/Achilleas1/',
            '/textures/costumes/Alonso1/',
            '/textures/costumes/donzuan1/',
            '/textures/costumes/ermis1/',
            '/textures/costumes/Romeo1/',
            '/textures/costumes/Sirina1/',
            '/textures/costumes/Tiresias1/',
            '/textures/costumes/Varonos1/',
            '/textures/costumes/Golfo2/',
            '/textures/costumes/KAdreas2/',
            '/textures/costumes/Yvoni2/',
            '/textures/costumes/Xotiko2/',
            '/textures/costumes/Achilleas2/',
            '/textures/costumes/Alonso2/',
            

          ];
          this.forema=[
            '369-911-GOLFO',
            '316-424-K ADREAS',
            '360-228-YVONI',
            '367-724-XOTIKO',
            '352-350-ACHILLEAS',
            '318-347-ALONSO',
            '263-596-DON JUAN ',
            '264-303-ERMIS',
            '330-274-ROMEO',
            '323-904-SIRINA',
            '353-TIRESIAS',
            '333-504-VARONOS FON ARPEN',
            '369-911-GOLFO',
            '316-424-K ADREAS',
            '360-228-YVONI',
            '367-724-XOTIKO',
            '352-350-ACHILLEAS',
            '318-347-ALONSO',
            '263-596-DON JUAN ',
            '264-303-ERMIS',
            '330-274-ROMEO',
            '323-904-SIRINA',
            '353-TIRESIAS',
            '333-504-VARONOS FON ARPEN',
            '369-911-GOLFO',
            '316-424-K ADREAS',
            '360-228-YVONI',
            '367-724-XOTIKO',
            '352-350-ACHILLEAS',
            '318-347-ALONSO',
            '263-596-DON JUAN ',
            
          ];
          
        // Load the textures
      const textureLoader = new THREE.TextureLoader();
      this.costumeTextures = []; // Initialize the array here
      let random = 55;
      let oneTime = 0;
      for (let i = 0; i < this.name.length; i++){
        // Big circle
        if(i<24){
            if (random > 72){
                random = 0 
            }
            
            if (this.path === this.name[i]) {
                for (let j = random; j >= 1; j--) {
                    const texture = textureLoader.load(this.path + this.forema[i] + j.toString() + '.png');
                    this.costumeTextures.push(texture); 
                }
                for (let j = 72; j > random; j--){
                    const texture = textureLoader.load(this.path + this.forema[i] + j.toString() + '.png');
                    this.costumeTextures.push(texture);                
                }
            }
            
            random += 3;
        }
        // Small Circle
        else{
            if(oneTime == 0){
                random = 55
            }
            oneTime+=1
            if (random > 72){
                random = 0 
            }
            
            if (this.path === this.name[i]) {
                for (let j = random; j >= 1; j--) {
                    const texture = textureLoader.load(this.path + this.forema[i] + j.toString() + '.png');
                    this.costumeTextures.push(texture); 
                }
                for (let j = 72; j > random; j--){
                    const texture = textureLoader.load(this.path + this.forema[i] + j.toString() + '.png');
                    this.costumeTextures.push(texture);                
                }
            }
            random += 13;
        }
        
      }
      
    }
    
    setMaterial() {
        // create a material with the array of textures
        this.material = new THREE.MeshBasicMaterial({
            map: this.costumeTextures[0],
            transparent: true,
            premultipliedAlpha: true,
            //opacity : 0     
        });
    }
    

    setMesh() {
        // create the mesh with the geometry and material
        this.mesh = new THREE.Mesh(this.geometry, this.material)
        // set the scale and position of the mesh
        this.mesh.scale.set(1.0, 1.0, 1.0)
        this.mesh.position.set(0, 0, 0)            
    }

    
    
    createCostume() {
        this.setGeometry()
        this.setTextures()
        this.setMaterial()
        this.setMesh()
        // add the mesh to the scene
        this.scene.add(this.mesh)
    }

    changeTexture() {
        const angle = -Math.atan2(this.camera.instance.position.x - this.mesh.position.x,
            this.camera.instance.position.z - this.mesh.position.z) + Math.PI;

        // calculate the index of the texture based on the angle between the camera and the costume
        const index = Math.floor((angle / (2 * Math.PI)) * this.costumeTextures.length);
        // update the material map with the new texture
        this.material.map = this.costumeTextures[index];
    }

    
    update() {
        
        if (this.camera.instance !== undefined) {

            this.mesh.lookAt(
                this.camera.instance.position.x,
                this.mesh.position.y,
                this.camera.instance.position.z);
        }
        this.changeTexture()

    }
}
