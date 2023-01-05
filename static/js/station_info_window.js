function clickHandler() {
  alert("something");
}

function postData() {
    const input = "This is data";
    $.ajax({
        type: "POST",
        url: "/window",
        data: { param: input },
        success: callbackFunc
    });
}

function callbackFunc(response) {
    // do something with the response
    console.log(response);
}