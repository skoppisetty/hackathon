var batchid = 0

$(document).ready(function() {
  checkAuthentication();
  // Certain UI components will be disabled if JS is. This overrides the css
  // that hides them (ingestion.ui.css), making sure they are shown.
  $(".js-required").not('.hidden').css("display", "inherit");
  if ($(".js-required").hasClass('hidden')) {
    $('#unsupported-browser-msg').show();
  }
});

var IMAGE_LICENSES = {
  "CC0": ["CC0", "(Public Domain)", "http://creativecommons.org/publicdomain/zero/1.0/"],
  "CC BY": ["CC BY", "(Attribution)", "http://creativecommons.org/licenses/by/4.0/"],
  "CC BY-SA": ["CC BY-SA", "(Attribution-ShareAlike)", "http://creativecommons.org/licenses/by-sa/4.0/"],
  "CC BY-NC": ["CC BY-NC", "(Attribution-Non-Commercial)", "http://creativecommons.org/licenses/by-nc/4.0/"],
  "CC BY-NC-SA": ["CC BY-NC-SA", "(Attribution-NonCommercial-ShareAlike)", "http://creativecommons.org/licenses/by-nc-sa/4.0/"]
};

initMainUI = function() {
  showLastBatchInfo();
  initCsvLicenseSelector();

  $("body").tooltip({
    selector: '[rel=tooltip]'
  });

  $.getJSON('/services/config', { name: "accountuuid"}, function(data) {
    $('#account-uuid-text').text('Account UUID: ' + data);
  });

  $('#logout-btn').click(function(e) {
    $.ajax({
      url: "/services/config",
      type: 'DELETE'
    }).done(function() {
      location.reload();
    });
  });

  // Set up csv-upload-form
  $('#csv-upload-form').validate({
    onfocusout: false,
    onkeyup: false,
    onsubmit: false,
    errorPlacement: function(error, element) {},
    highlight: function(element) {
      $(element).closest('.control-group').addClass('error');
    },
    unhighlight: function(element) {
      $(element).closest('.control-group').removeClass('error');
    },
    rules: {
      csvpath: {
        required: true
      }
    }
  });

  $('#csv-upload-form').submit(function(event) {
    event.preventDefault();
    if ($('#csv-upload-form').valid()) {
      var values =
        "{\'CSVfilePath\':\'" + processFieldValue('#csv-path') +
        "\',\'RightsLicense\':\'" + processFieldValue('#csv-license-dropdown') +
        "\'}";
      postCsvUpload("new", values);
    }
    else {
      showAlert('The CSV file path cannot be empty.');
    }
    $("#upload-alert").hide();
  });

  $('#result-csv-gen-form').validate({
    onfocusout: false,
    onkeyup: false,
    onsubmit: false,
    errorPlacement: function(error, element) {},
    highlight: function(element) {
      $(element).closest('.control-group').addClass('error');
    },
    unhighlight: function(element) {
      $(element).closest('.control-group').removeClass('error');
    },
    rules: {
      resultcsvgenpath: {
        required: true
      }
    }
  });

  $('#result-csv-gen-form').submit(function(event) {
    event.preventDefault();
    if ($('#result-csv-gen-form').valid()) {
      var values =
        "{\'batch_id\':\'0" +
        "\',\'target_path\':\'" + processFieldValue('#result-csv-gen-path') +
      "\'}";
      postResultCSVGen(values);
    }
    else {
      showAlert('The result CSV file cannot be empty.');
    }
  });

  $('#result-zip-gen-form').submit(function(event) {
    event.preventDefault();
    var values =
      "{\'batch_id\':\'0" +
      "\',\'target_path\':\'" + processFieldValue('#result-zip-gen-path') +
    "\'}";
    postResultZipGen(values);
  });

  initHistoryUI();
  initCSVGenUI();
}

checkAuthentication = function() {
  blockUI();

  $.getJSON('/services/auth', function(data) {
    $.unblockUI();
    if (!data) {
      initLoginModal();
    } else {
      initMainUI();
    }
  })

  .error(function(data) {
    $.unblockUI();
    $('#serviceErrorModal').modal();
  });
}

blockUI = function() {
  var div = document.createElement("div");
  var throb = new Throbber({
    color: 'white',
    padding: 30,
    size: 100,
    fade: 200,
    clockwise: false
  }).appendTo(div).start();
  $.blockUI.defaults.css = {};
  $.blockUI({
    message: div
   });
}

initLoginModal = function() {
  $('#loginModal').modal();

  $('#login-form').validate({
    onkeyup: false,
    errorElement:'span',
    errorClass:'help-inline',
    highlight: function(element, errorClass, validClass) {
      $(element).closest('.control-group').addClass('error');
    },
    unhighlight: function (element, errorClass, validClass) {
      $(element).parents(".error").removeClass('error');
    },
    rules: {
      accountuuid: {
        rangelength: [32, 36],
        required: true
      },
      apikey: {
        rangelength: [32, 36],
        required: true
      }
    }
  });

  $('#login-button').click(function(event) {
    event.preventDefault();
    if ($('#login-button').attr('disabled')) {
      return;
    }

    if (!$('#login-form').valid()) {
      return;
    }

    var accountuuid = $("#accountuuid").val();
    var apikey = $("#apikey").val();

    $('#login-button').attr('disabled', true);
    $('#login-button').addClass('disabled');
    new Throbber({
      color: '#005580',
      size: 20
    }).appendTo($('#login-error')[0]).start();

    $.post('/services/auth', { accountuuid: accountuuid, apikey: apikey },
      function(data) {
      $('#login-form > .control-group').removeClass('error');
      $('#login-error').addClass('hide');
      $('#loginModal').modal('hide');
      initMainUI();
    }, 'json')
    .error(function(err) {
      if (err.status == 409) {
        $('#login-error').html(
          'Incorrect Account UUID and API Key combination..');
        $('#login-button').attr('disabled', false);
        $('#login-button').removeClass('disabled');
      } else {
        $('#login-error').html(
          'Cannot sign in due to iDigBio service unavailable. ' +
          'Please come back later.');
      }
      $('#login-form > .control-group').addClass('error');
      $('#login-error').removeClass('hide');
      $('#login-button').attr('disabled', false);
      $('#login-button').removeClass('disabled');
    });
  });
}

initCsvLicenseSelector = function() {
  $.each(IMAGE_LICENSES, function(key, value) {
    var option = ["<option value=\"", key, "\">", value[0], " ",
      value[1], "</option>"].join("");
    $("#csv-license-dropdown").append(option);
  });
  $("#csv-license-dropdown option[value='']").remove();

  $("#csv-license-dropdown").change(function(e) {
    var licenseName = $("#csv-license-dropdown").val();
    var license = IMAGE_LICENSES[licenseName];
    showAlert(["The images will be uploaded under the terms of the ",
        license[0], " ", license[1], " license (see <a href=\"", license[2],
        "\" target=\"_blank\">definition</a>)."].join(""),
      null, "alert-info");
    setPreference('imagelicense', licenseName);
  });
}

postResultCSVGen = function(values) {
  var callback = function(resultObj) {
    container = "#result-alert-container";
    var alert_html =
      ['<div class="alert alert-block fade span10" id="result-alert">',
       '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="result-alert-text">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#result-alert").show();
    $("#result-alert").addClass('in');
    if (resultObj.error == "") {
      $("#result-alert").addClass("alert-success");
      $("#result-alert-text").html("The CSV file is successfully saved to: "
          + resultObj.path);
    } else {
      $("#result-alert").addClass("alert-error");
      $("#result-alert-text").html(resultObj.error);
    }
  };

  $.getJSON("/services/genoutputcsv", {values: values}, callback);
}

postResultZipGen = function(values) {
  var callback = function(path){
    container = "#result-alert-container";
    var alert_html =
      ['<div class="alert alert-block fade span10" id="result-alert">',
       '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="result-alert-text">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#result-alert").show();
    $("#result-alert").addClass('in');
    $("#result-alert").addClass("alert-success");
    $("#result-alert-text").html("The zip file is successfully saved to: "
        + path);
  };

  $.getJSON("/services/genoutputzip", {values: values}, callback);
}

postCsvUpload = function(action, values) {
  // Reset the elements
  $("#result-table-container").removeClass('in');
  $("#result-table-container").removeClass('hide');
  $("#progressbar-container").removeClass('in');
  $("#progressbar-container").removeClass('hide');

  var callback = function(dataReceived){
    // Disable inputs only if task succesfully added
    if(dataReceived['error']){
      var errMsg = "<strong>Error! </strong>" + dataReceived['error'];
      showAlert(errMsg)
    }
    else{
      $('#csv-license-dropdown').attr('disabled', true);
      $("#csv-license-dropdown").addClass('disabled');

      $('#csv-path').attr('disabled', true);
      $("#csv-path").addClass('disabled');

      $("#csv-upload-button").attr('disabled', true);
      $("#csv-upload-button").addClass('disabled');

      // Clean up UI.
  //    $("#upload-alert").alert('close');
      // Show progress bar in animation
      $(".progress-primary").addClass('active');
      $("#progressbar-container").addClass('in');
      setTimeout(function() {
      updateProgress(dataReceived['task_id']);
      }, 1000)
    }
  };

  // now send the form and wait to hear back
  if (action == "new") {
    $.post('/services/ingest', { values: values }, callback, 'json')
    .error(function(data) {
      var errMsg = "<strong>Error! </strong>" + data.responseText;
      showAlert(errMsg)
    });
  } else {
    $.post('/services/ingest', callback, 'json')
    .error(function(data) {
      var errMsg = "<strong>Error! </strong>" + data.responseText;
      showAlert(errMsg);
    });
  }
}

showLastBatchInfo = function() {
  $.getJSON('/services/lastbatchinfo', function(batch) {
    if (batch.Empty) {
      return;
    }

    if (!batch.finished) {
      var start_time = batch.start_time;
      var errMsg = ['<p><strong>Warning!</strong> '
        + 'Your last upload from directory/CSV file ',
        batch.path, ' which started at ', start_time,
        ' was not entirely successful.</p>'].join("");
      var extra = '<p><button id="retry-button" type="submit"'
        + ' class="btn btn-warning">Retry failed uploads</button></p>';
      showAlert(errMsg, extra, "alert-warning");
      $("#retry-button").click(function(event) {
        event.preventDefault();
        $("#upload-alert").alert('close');
        // TODO: Differentiate the CSV task or dir task.
        postCsvUpload("retry");
        // Note: retry will reload the batch information, and read the CSV file
        // again.
      });
    }
  }, "json");
}

/**
 * Display an alert message in the designated alert container.
 * Param:
 *   {HTML string} message
 *   {HTML string} [additionalElement] Additional element(s) in the second row.
 *   {String} [alertType] The alert type, i.e. Bootstrap class, default to
 *   alert-error.
 */
showAlert = function(message, additionalElement, alertType) {
  additionalElement = additionalElement || "";
  alertType = alertType || "alert-error";
  container = "#alert-container";

  var alert_html =
    ['<div class="alert alert-block fade span10" id="upload-alert">',
    '<button class="close" data-dismiss="alert">&times;</button>',
    '<p id="alert-text">',
    '<div id="alert-extra">',
    '</div>'].join('\n');
  $(container).html(alert_html);
  $("#upload-alert").show();
  $("#upload-alert").addClass('in');
  $("#upload-alert").addClass(alertType);
  $("#alert-text").html(message);
  $("#alert-extra").html(additionalElement);
}

updateProgress = function(task_id) {
  // dummy query string is added not to allow IE retrieve results
  // from its browser cache.
  // added by Kyuho in July 23rd 2013
  var url = '/services/ingestionprogress?&task_id='+ task_id + '&now=' + $.now();

  $.getJSON(url, function(progressObj) {
    console.log(progressObj);
    var progress = progressObj.total == 0 ? 100 :
      Math.floor((progressObj.successes + progressObj.fails +
        progressObj.skips) / progressObj.total * 100);

    var csvfileuploaded = "";
    if (progress == 100) {
      if (progressObj.successes == 0) {
        csvfileuploaded = "No CSV file is generated.";
      } else if (progressObj.csvuploaded) {
        csvfileuploaded = "CSV file is uploaded.";
      } else if (progressObj.finished){
        csvfileuploaded = "CSV file upload failed.";
      }
    }

    $("#progresstext").text(
      ["Progress: (Successful:" + progressObj.successes,
       ", Skipped: " + progressObj.skips,
       ", Failed: " + progressObj.fails,
       ", Total to upload: " + progressObj.total,
       ". " + csvfileuploaded,
       ")"].join(""));

    $("#upload-progressbar").width(progress + '%');

    if (progressObj.fatal_server_error) {
      var errMsg = ["<p><strong>Warning!</strong> ",
		    "<p>FATAL SERVER ERROR</p> ",
		    "<p>Server under maintenance. Try Later</p>", ].join("");
      showAlert(errMsg, extra, "alert-warning");
    } else if (progressObj.input_csv_error) {
      var errMsg = ["<p><strong>Input CSV FILE ERROR</strong> ",
                    "<p>Your input CSV file is weird</p> ",
                    "<p>THis error occurs when your CSV file has different number",
                    " of columns among rows or any field contains double quatation",
                    " mark(\")</p>", ].join("");
      showAlert(errMsg, extra, "alert-warning");
    } else if (progressObj.finished) {
      $(".progress-primary").toggleClass('active');

      $('#csv-license-dropdown').attr('disabled', false);
      $("#csv-license-dropdown").removeClass('disabled');

      $('#csv-path').attr('disabled', false);
      $("#csv-path").removeClass('disabled');

      $("#csv-upload-button").attr('disabled', false);
      $("#csv-upload-button").removeClass('disabled');

      if (progressObj.successes == 0) {
        $("#result-gen-container").addClass('in');
        $("#result-gen-container").addClass('hide');
      }
      else {
        $("#result-gen-container").removeClass('in');
        $("#result-gen-container").removeClass('hide');
      }

      if (progressObj.fails > 0 || progressObj.total == 0) {
        if (progressObj.fails > 0) {
          var errMsg = ["<p><strong>Warning!</strong> ",
            "This upload was not entirely successful. ",
            "You can retry it at a later time."].join("");
          if (progress < 100) {
            errMsg += [' Upload aborted before all images are tried ',
              'due to continuing erroneous network conditions.'].join('');
          }
          var extra = ['<p><button id="retry-button" type="submit"',
            'class="btn btn-warning">Retry failed uploads</button></p>'].join("");
        } else {

          var errMsg = ["<p><strong>Warning!</strong> ",
            "Nothing is uploaded. Maybe the CSV is empty or the network is down? ",
            "Please check the folder and network connection and ",
            "retry it by clicking the 'Upload' button."].join("");

        }
        showAlert(errMsg, extra, "alert-warning");
        $("#retry-button").click(function(event) {
          event.preventDefault();
          $("#upload-alert").alert('close');
          // TODO: Differentiate the CSV task or dir task.
          postCsvUpload("retry");
        });
      }

      if(progressObj.fails == 0 && progressObj.total > 0 ) {
        showAlert("All images are successfully uploaded!", "", "alert-success");
      }

      if (progressObj.total > 0) {
        // If we haven't tried one file, no need to get results.
        $.getJSON('/services/ingestionresult', renderResult);
      }
    } else {
      // Calls itself again after 1000ms.
      setTimeout(function() {
        updateProgress(task_id);
      }, 1000)
      // setTimeout("updateProgress ()", 1000);
    }
  });
}

renderResult = function(data) {
  $('#result-table-container').addClass('in');
  $('#result-table').dataTable({
    "aaData": data,
    "aoColumns": [
      { "sTitle": "OriginalFileName", "sWidth": "42%" },
      { "sTitle": "Online Path or Error Message", "sWidth": "58%",
        "fnRender": function(obj) {
          error = obj.aData[1]; // It is given as an array.
          url = obj.aData[2];
          var text;
          if (error != "") {
            text = "<span class=\"label label-important\">" + error + "</span>"
          } else if (url == null) {
            text = "<span class=\"label label-important\">"
              + "This image is not successfully uploaded.</span>"
          } else {
            text = '<a target="_blank" href="' + url + '">'+ url + '</a>';
          }
          return text;
        }
      } // 3 elements.
    ],
    "sDom": "<'row'<'span5'l><'span6'p>>tr<'row'<'span6'i>>",
    "bPaginate": true,
    "bLengthChange": true,
    "bFilter": false,
    "bSort": true,
    "bInfo": true,
    "bAutoWidth": false,
    "bDestroy" : true,
    "sPaginationType": "bootstrap"
  });
}

getPreference = function(name, callback) {
  $.getJSON('/services/config', { name: name }, function(data) {
    callback(data);
  })
  .error(function(data) {
    callback(null);
  });
}

setPreference = function(name, val) {
  $.post('/services/config', { name: name, value: val }, function() { }, 'json');
}

// Process the special values like \, ', ". Note that " is replaced with '.
processFieldValue = function(name) {
  return $(name).val().replace(/\\/g,"\\\\").replace(/'/g,"\\'").replace(/"/g,"\\'")
}
