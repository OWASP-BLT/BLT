$(document).ready(function(){
			var lines = $('.hero .text-slider-line');
			var i = 2;
			var n = lines.length;	
			var changeText = setInterval(function(){
				console.log(i);
				console.log(lines);
				console.log(lines[i].className);
				$(lines[i]).fadeOut();
				if(i==(n-1)){
					i=0;
				}
				else{
					i++;
				}
				$(lines[i]).fadeIn();
			},2000);


		// var change = setInterval(function(){
		// 	// lines.each(function(index, ele){
		// 	// 	console.log(ele)
		// 	// 	var k = setTimeout(function(){
		// 	// 	$(ele).fadeOut();
		// 	// 	console.log(ele)},1000)

		// 	// 	$(ele).next().fadeIn();

		// 	// }
		// 	// 	)
		// 	var i = 0;
		// 	var l = lines.length;
		// 	var k = setInterval(function(){
		// 		console.log(i);
		// 		console.log(lines);
		// 		console.log(lines[i].className);
		// 		$(lines[i]).fadeOut();
		// 		if(i==(n-1)){
		// 			clearInterval(k)
		// 		}
		// 		else{
		// 			i++;
		// 		}
		// 		$(lines[i]).fadeIn();
		// 	},1000)
		// },4000)
});