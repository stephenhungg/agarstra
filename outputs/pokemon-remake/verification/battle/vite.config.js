import path from 'node:path';
import {fileURLToPath} from 'node:url';
export default{resolve:{alias:{three:path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../app/node_modules/three')}},server:{fs:{allow:[path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../../..')]}}};
