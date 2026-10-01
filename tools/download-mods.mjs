// Resolve pinned stable versions and verify their SHA-512 before installation.
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,basename} from 'node:path';
const instance=process.argv[2];
if(!instance || basename(instance)!=='Aqualumen Lab') throw new Error('Target must be the isolated Aqualumen Lab instance');
const mods=resolve(instance,'minecraft/mods');
await mkdir(mods,{recursive:true});
const lock=[];
for(const id of ['zsoi0dso','26nVNc41']) {
    const response=await fetch(`https://api.modrinth.com/v2/version/${id}`,{headers:{'User-Agent':'Aqualumen-local-development/0.1'}});
    if(!response.ok) throw new Error(`Version lookup ${response.status}`);
    const version=await response.json();
    if(version.version_type!=='release'||!version.game_versions.includes('1.21.1')||!version.loaders.includes('fabric')) throw new Error('Unexpected version compatibility');
    const file=version.files.find(f=>f.primary);
    if(!file || basename(file.filename)!==file.filename) throw new Error('Invalid filename');
    const downloaded=await fetch(file.url);
    if(!downloaded.ok) throw new Error(`Download ${downloaded.status}`);
    const data=Buffer.from(await downloaded.arrayBuffer());
    if(createHash('sha512').update(data).digest('hex')!==file.hashes.sha512) throw new Error('SHA-512 mismatch');
    const path=resolve(mods,file.filename);
    try { if(!data.equals(await readFile(path))) throw new Error('Existing file differs'); }
    catch(error) { if(error.code!=='ENOENT') throw error; await writeFile(path,data,{flag:'wx'}); }
    lock.push({project:version.project_id,version:version.version_number,url:file.url,sha512:file.hashes.sha512});
    console.log(`Verified ${file.filename}`);
}
await mkdir('build',{recursive:true});
const mappingUrl='https://maven.fabricmc.net/net/fabricmc/intermediary/1.21.1/intermediary-1.21.1.jar';
const mappingResponse=await fetch(mappingUrl);
if(!mappingResponse.ok) throw new Error(`Mapping download ${mappingResponse.status}`);
const mappingData=Buffer.from(await mappingResponse.arrayBuffer());
const mappingHash='6059157dfb4a536ec151697004f74f6004b7d346b289c2f89849e0e585aa36fa';
if(createHash('sha256').update(mappingData).digest('hex')!==mappingHash) throw new Error('Intermediary mapping SHA-256 mismatch');
const libraryDir=resolve(instance,'../../libraries/net/fabricmc/intermediary/1.21.1');
await mkdir(libraryDir,{recursive:true});
const mappingPath=resolve(libraryDir,'intermediary-1.21.1.jar');
try { if(!mappingData.equals(await readFile(mappingPath))) throw new Error('Existing mapping JAR differs'); }
catch(error) { if(error.code!=='ENOENT') throw error; await writeFile(mappingPath,mappingData,{flag:'wx'}); }
lock.push({project:'net.fabricmc:intermediary',version:'1.21.1',url:mappingUrl,sha256:mappingHash});
console.log('Verified intermediary-1.21.1.jar');
await writeFile('build/mods-lock.json',JSON.stringify(lock,null,2)+'\n');
