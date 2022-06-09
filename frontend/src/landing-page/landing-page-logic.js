
const updateTime = () =>{
    const today = new Date();
    const curHr = today.getHours();

    if (curHr < 12) {
      return 'morning';
    } else if (curHr < 18) {
      return 'afternoon';
    } else {
      return 'evening';
    }
  }
export {updateTime}