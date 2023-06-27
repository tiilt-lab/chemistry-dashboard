import { adjDim } from '../myhooks/custom-hooks';

function Instruction(props){
    return(
    <div className="instruction" style = {{width: adjDim(343) + 'px',}}>
      {props.instructions}
      </div>
    )
  }

  export {Instruction}
