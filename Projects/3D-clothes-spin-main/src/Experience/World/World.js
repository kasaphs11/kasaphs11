import Experience from '../Experience.js';
import Environment from './Environment.js';
import Costume from './Costume.js';
import * as THREE from 'three';
import Museum from './Museum.js';
import Stats from 'three/examples/jsm/libs/stats.module';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import Base from './Base.js';
import Photo_Stant from './Photo_Stant.js';

import { Vector3, BoxBufferGeometry, MeshBasicMaterial, Mesh } from 'three';
import Renderer from '../Renderer.js';

export default class World {
    constructor() {
        // Create an instance of the Experience class
        this.experience = new Experience();
        // Reference to the scene from the Experience class
        this.scene = this.experience.scene;
        // Reference to the resources from the Experience class
        this.resources = this.experience.resources;
        this.positions = [];
        this.Stant_positions = [];
        this.Helper();

        // Get the camera instance from the Experience class
        this.camera = this.experience.camera.instance;
        
        // Array of costume names to be loaded
        this.costumeNames = ['Golfo/','KAdreas/','Yvoni/','Xotiko/','Achilleas/','Alonso/','donzuan/','ermis/','Romeo/','Sirina/','Tiresias/','Varonos/','Golfo1/','KAdreas1/','Yvoni1/','Xotiko1/','Achilleas1/','Alonso1/','donzuan1/','ermis1/','Romeo1/','Sirina1/','Tiresias1/','Varonos1/','Golfo2/','KAdreas2/','Yvoni2/','Xotiko2/','Achilleas2/','Alonso2/']; // TODO: Make a json or something
        
        // // General path to all the available costumes
        this.path = '/textures/costumes/';

        this.createCostumesInCircle(24, 16, 15,'costume');
        this.createCostumesInCircle(6, 6, 60,'costume');
        this.createCostumesInCircle(6, 23, 60,'stand');

        // Wait for resources to be ready before setting up the world
        this.resources.on('ready', () => {
            // Init the array with the costumes
            this.costumeArray = [];

            // Load the costumes and fill the array
            this.loadCostumes();
            
            // Load Stants
            this.loadStants();

            // Send costumes to the MouseListener as well 
            this.experience.mouseListener.setCostumes(this.costumeArray)

            this.experience.opacityManager.setCostumes(this.costumeArray)

            // Set up the Environment
            this.environment = new Environment();

            // Create a new Museum instance
            this.museum = new Museum();

            
            this.Base = new Base();

        });
    }
    createCostumesInCircle(count, radius, angleInterval , type) {
        if(type == 'costume')
            for (let i = 0; i < count; i++) {
                    const angle = (i * angleInterval) * (Math.PI / 180); // Convert to radians
                    const x = radius * Math.cos(angle);
                    const z = radius * Math.sin(angle);
                    this.positions.push({x,y:0.35,z})
            }
        else if(type == 'stand'){
            for (let i = 0; i < count; i++) {
                const angle = (i * angleInterval) * (Math.PI / 180); // Convert to radians
                const x = radius * Math.cos(angle);
                const z = radius * Math.sin(angle);
                this.Stant_positions.push({x,y:-0.76,z})
            }
        }
    }
    // Method to load costumes and create costume objects
    loadCostumes() {
        let costumeIDCounter = 0;
        
        for (let i = 0; i < this.positions.length; i++) {
            // Create a new costume
            let costume = new Costume(this.path + this.costumeNames[i]);
            
            // Set the unique ID for each costume
            costume.mesh.userData.id = costumeIDCounter;
            costumeIDCounter++;

            // Set the position of the costume in the grid
            costume.mesh.position.copy(this.positions[i]);
            
            // Add the costume to the array
            this.costumeArray.push(costume);    
        }
        
    }
    loadStants() {
        // Loop through each stant position
        let angle = 0
        for (let i = 0; i < this.Stant_positions.length; i++) {
            
            const stantPosition = this.Stant_positions[i];
            const rotate = Math.PI/2 + angle
            // Create an instance of the Photo_Stant class and pass the position
            const photoStant = new Photo_Stant(stantPosition, rotate);
    
            // Add the Photo_Stant model to the scene
            this.scene.add(photoStant.model);
            angle-=60 * (Math.PI / 180)
        }
    }
    Helper(){
        this.stats = new Stats();
        document.body.appendChild(this.stats.dom);

        this.axesHelper = new THREE.AxesHelper(100);
        this.scene.add( this.axesHelper );

        this.gridHelper = new THREE.GridHelper(100,100);
        //.this.scene.add(this.gridHelper)
    }
    
    // Update method to animate the camera and update costumes
    update() {
        // Update stats
        this.stats.update();
       
        if (this.costumeArray !== undefined) {
            // Loop through all of them
            for (let i = 0; i < this.costumeArray.length; i++) {
                // If the costume exists
                if (this.costumeArray[i]) {
                    // Update the costume
                    this.costumeArray[i].update();
                }
            }
        }  
    }
}
