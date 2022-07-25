import style from './features.module.css'
import {DialogBox} from '../dialog/dialog-component'
import questIcon from "../assets/img/question.svg"

function FeaturePage(props){
  return(
    <>
      <div>
          <table className={style["features-table"]}>
                <thead>
                  <tr>
                    <th className={style["desc-header"]}>Classifier</th>
                    <th className={style["score-header"]}>Score</th>
                    <th className={style["graph-header"]}>Graph</th>
                  </tr>
                </thead>
                <tbody>
                    {props.features.map((feature, index)=>(
                        <tr key={index}>
                            <td>
                              <img alt='quest' onClick={()=> props.getInfo(feature.name)} className={style["info-button"]} src={questIcon}/>
                                { feature.name }
                            </td>
                            <td className={style.score}>
                              <div className={style.number}>{Math.round(feature.average)} </div>
                              <div className= {feature.trend == 1 ? `${style["direction-indicator"]} ${style.positive}` : feature.trend == 0 ? `${style["direction-indicator"]} ${style.neutral}` : feature.trend == -1 ? `${style["direction-indicator"]} ${style.negative}` : style["direction-indicator"]} > </div>
                            </td>
                            <td>
                              {feature.values.length == 0 ? <span className={style["no-data-span"]} style={{width: "74px"}}></span> : <></> }
                              <svg viewBox="0 -0.5 74 39.5" className={style.svg}>
                                <path d={feature.path} fill="none" className={feature.trend >= 0 ? style.positive : feature.trend == -1 ? style.negative : ""} ></path>
                              </svg>
                            </td>
                      </tr>))   
                  }
                </tbody>
            </table>
        </div>

      <DialogBox
        itsclass= {"add-dialog"}
        heading={props.featureHeader}
        message={props.featureDescription}
        show={props.showFeatureDialog }
        closedialog={props.closeDialog} 
      />
    </>
  )
}

export {FeaturePage}