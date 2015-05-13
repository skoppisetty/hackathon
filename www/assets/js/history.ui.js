var batchid = 0

initHistoryUI = function() {
  $('#refresh-bh-button').click(function(event) {
    $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);
  });

  $('#history-tab-button').click(function(event) {
    $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);
  });

  $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);

 $('#download-all-csv-form').submit(function(event) {
    event.preventDefault();
    var values =
      "{\'target_path\':\'" + processFieldValue('#download-all-csv-path') +
      "\'}";
    postAllCSVGen(values);
  });

  $('#hist-csv-gen-form').submit(function(event) {
    event.preventDefault();
    if ($('#hist-csv-gen-form').valid()) {
      var values =
        "{\'batch_id\':\'0" +
        "\',\'target_path\':\'" + processFieldValue('#hist-csv-gen-path') +
      "\'}";
      postHistCSVGen(values);
    }
    else {
      showAlert('The CSV file path cannot be empty.');
    }
  });

  $('#hist-zip-gen-form').submit(function(event) {
    event.preventDefault();
    var values =
      "{\'batch_id\':\'" + batchid +
      "\',\'target_path\':\'" + processFieldValue('#hist-zip-gen-path') +
      "\'}";
    postHistZipGen(values);
  });
}

postHistZipGen = function(values) {
  var callback = function(path){
    container = "#hist-alert-container";
    var alert_html =
      ['<div class="alert alert-block fade span10" id="hist-alert">',
       '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="hist-alert-text">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#hist-alert").show();
    $("#hist-alert").addClass('in');
    $("#hist-alert").addClass("alert-success");
    $("#hist-alert-text").html("The zip file is successfully saved to: "
        + path);
  };

  $.getJSON("/services/genoutputcsv", {values: values}, callback);
}

renderBatchHistory = function(data) {
  if ($('#batch-history-table-container').hasClass('hide')) {
    $('#batch-history-table-container').removeClass('hide');
    $('#batch-history-table-container').addClass('in');
  }

  var bht = $('#batch-history-table').dataTable({
    "aaData": data,
    "aoColumns": [
      { "sTitle": "ID", "sWidth": "5%" },
      { "sTitle": "CSV File Path", "sWidth": "25%" },
      { "sTitle": "iDigbio Provided By GUID", "bVisible": false },
      { "sTitle": "Rights License", "bVisible": false },
      { "sTitle": "Rights License Statement Url", "bVisible": false },
      { "sTitle": "Rights License Logo Url", "bVisible": false },
      { "sTitle": "Start Time", "sWidth": "15%" },
      { "sTitle": "Finish Time", "bVisible": false },
      { "sTitle": "Total Records", "sWidth": "5%" },
      { "sTitle": "Failed Records", "sWidth": "5%" },
      { "sTitle": "Skipped Records", "sWidth": "5%" },
      { "sTitle": "Successfull Records", "sWidth": "5%" }

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
  
  // We do the row selection here outside datatable, 
  // because the dataTable is not doing well in supporting row selections.
  $('#batch-history-table').delegate('tbody > tr > td', 'click', function (event)
  {
    $(bht.fnSettings().aoData).each(function (){
        $(this.nTr).removeClass('success');
        $(this.nTr).removeClass('row_selected');
        });

    if (! $(this.parentNode).hasClass('row_selected')) {
      $(this.parentNode).addClass('success');
      $(this.parentNode).addClass('row_selected');
    }

    var aData = bht.fnGetData( this.parentNode );//get data of the clicked row
    batchid = aData[0];
    $.getJSON('/services/history', { table_id: aData[0] }, 
              renderMediaRecordHistory);
    $('#image-history-table-description').text("Batch ID: " + aData[0]);
  });
}

renderMediaRecordHistory = function(data) {
  if ($('#image-history-table-container').hasClass('hide')) {
    $('#image-history-table-container').removeClass('hide');
    $('#image-history-table-container').addClass('in');
  };
  $('#image-history-table').dataTable({
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

postHistCSVGen = function(values) {
  var callback = function(resultObj) {
    container = "#hist-alert-container";
    var alert_html =
      ['<div class="alert alert-block fade span10" id="hist-alert">',
       '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="hist-alert-text">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#hist-alert").show();
    $("#hist-alert").addClass('in');
    if (resultObj.error == "") {
      $("#hist-alert").addClass("alert-success");
      $("#hist-alert-text").html("The CSV file is successfully saved to: "
          + resultObj.path);
    } else {
      $("#hist-alert").addClass("alert-error");
      $("#hist-alert-text").html(resultObj.error);
    }
  };

  $.getJSON("/services/genoutputcsv", {values: values}, callback);
}

postAllCSVGen = function(values) {
  var callback = function(resultObj){
    container = "#hist-alert-container2";
    var alert_html =
      ['<div class="alert alert-block fade span10" id="hist-alert2">',
       '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="hist-alert-text2">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#hist-alert2").show();
    $("#hist-alert2").addClass('in');
    if (resultObj.error == "") {
      $("#hist-alert2").addClass("alert-success");
      $("#hist-alert-text2").html("The CSV file is successfully saved to: "
          + resultObj.path);
    } else {
      $("#hist-alert2").addClass("alert-error");
      $("#hist-alert-text2").html(resultObj.error);
    }
  };

  $.getJSON("/services/generateallcsv", {values: values}, callback);
}

