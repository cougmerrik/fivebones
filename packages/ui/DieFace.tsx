import React from 'react';
import pip1 from '../../pip1.png';
import pip2 from '../../pip2.png';
import pip3 from '../../pip3.png';
import pip4 from '../../pip4.png';
import pip5 from '../../pip5.png';
import pip6 from '../../pip6.png';

const faces = [pip1, pip2, pip3, pip4, pip5, pip6];
export function DieFace({value,assetUrl=(url:string)=>url,decorative=false}:{value:number;assetUrl?:(url:string)=>string;decorative?:boolean}) {
 return <img className="pip-image" src={assetUrl(faces[value-1])} alt={decorative?'':String(value)} aria-hidden={decorative?true:undefined} draggable={false} width={1254} height={1254}/>;
}
