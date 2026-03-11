import * as THREE from 'three';
import Experience from '../Experience.js';

export default class PhotoStand {
    constructor(position, rotation) {
        this.experience = new Experience();
        this.scene = this.experience.scene;
        this.resources = this.experience.resources;
        this.resource = this.resources.items.Photo_Stand_Model;
        this.rotation = rotation;
        this.position = position;

        this.setModel();
    }

    loadTextures() {
        this.textureLoader = new THREE.TextureLoader();

        this.bakedTexture = this.textureLoader.load(this.bakedTexturePath);
        this.bakedTexture.flipY = false;

        this.diffuseTexture = this.textureLoader.load('models/Photo Stand/Photo_Stand_Diffuse.jpg');
        this.diffuseTexture.anisotropy = 32;
        this.diffuseTexture.flipY = false;
    }

    createModel() {
        this.model = this.resource.scene.clone();
        this.model.scale.set(1, 1, 1);
        this.model.position.copy(this.position);
        this.model.rotation.set(0, this.rotation, 0);

        this.model.traverse((child) => {
            if (child instanceof THREE.Mesh) {
                const customMaterial = new THREE.MeshBasicMaterial({
                    map: this.diffuseTexture,
                });
                child.material = customMaterial;
            }
        });
    }

    addAxesHelper() {
        const axesHelper = new THREE.AxesHelper(3);
        axesHelper.position.copy(this.model.position);
        axesHelper.rotation.copy(this.model.rotation);
        this.scene.add(axesHelper);
    }

    setModel() {
        this.loadTextures();
        this.createModel();
        this.addAxesHelper();
        this.scene.add(this.model);
    }
}
