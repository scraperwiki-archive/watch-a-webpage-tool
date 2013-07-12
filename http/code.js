// settings is a json object containing information
// about this tool (source) and its parent dataset (target)
settings = scraperwiki.readSettings()

$(function(){
  populateSingleSqlValues() 
  populateSqlTables() 
})

function populateSingleSqlValues() {
  $('span[data-sql]').each(function() {
    var span = $(this)
    var sqlQuery = span.attr('data-sql')
    span.html('<img src="loader-btn-default.gif" width="16" height="16"> loading')
    span.addClass('muted')

    scraperwiki.sql(sqlQuery, function(data){
      console.log(data)
      if(data.length == 1 && _.size(data[0]) == 1) {
        span.html(_.values(data[0])[0]) // Yelp, span can change
        span.removeClass('muted')
      }
      else {
        span.addClass('text-error').removeClass('muted')
        span.html('<img src="exclamation.png"> Expected single value, got ' + data.length)
      }
    
    }, function(jqXHR, textStatus, errorThrown) {
      span.addClass('text-error').removeClass('muted')
      span.html('<img src="exclamation.png"> Error encountered: ' + jqXHR.responseText)
    })
  })
}

function populateSqlTables() {

  $('table[data-sql]').each(function() {
    var table = $(this)
    var sqlQuery = table.attr('data-sql')
    table.html('<tr><td><img src="loader-btn-default.gif" width="16" height="16"> loading</td></tr>')     

    scraperwiki.sql(sqlQuery, function(data){
      console.log(this)
      table.empty()
      if(data.length) {
        thead = $('<thead>').appendTo(table)
        tbody = $('<tbody>').appendTo(table)
        tr = $('<tr>').appendTo(thead)
        for(columnName in data[0]) {
          $('<th>').appendTo(tr).html(columnName)
        }
        _.each(data, function(row) { // row is columnName, value
          tr = $('<tr>').appendTo(tbody)
          _.each(row, function(cellValue, columnName) {
            $('<td>').appendTo(tr).html(cellValue)
          })
        })
      } else {
        table.html('<tr><td class="muted"><img src="information.png"> No results for query: <code>' + 
                   sqlQuery + '</code></td></tr>')     
      }
    }, function(jqXHR, textStatus, errorThrown){
      table.html('<tr><td class="text-error"><img src="exclamation.png"> Error encountered: ' 
                 + jqXHR.responseText + '</td></tr>')
    })
  })
}
