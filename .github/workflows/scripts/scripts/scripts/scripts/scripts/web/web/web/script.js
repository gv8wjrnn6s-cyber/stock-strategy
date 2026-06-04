document.addEventListener('DOMContentLoaded', function(){
    if(typeof netValueData !== 'undefined' && netValueData.length > 1){
        var labels = netValueData.map(d => d.date);
        var values = netValueData.map(d => d.net_value);
        var ctx = document.getElementById('chart').getContext('2d');
        new Chart(ctx, {type:'line', data:{labels:labels, datasets:[{label:'净值',data:values,borderColor:'#1e3a8a',fill:false}]}, options:{responsive:true}});
    }
});
