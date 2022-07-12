
import style from './spinner.module.css'
function AppSpinner() {

  return(
    <div className={style["lds-ring"]}><div></div><div></div><div></div><div></div></div>
  )

}

export {AppSpinner}
