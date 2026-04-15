export const jsonToStr = (obj)=>{
    try{
        return JSON.stringify(obj)
    }catch(error) {
        return ""
    }
}

export const strToJson = (str,isList = false) =>{
    try{
        return JSON.parse(str)
    }catch(error){
        return isList ? []:{}
    }
}