$(document).ready(function(){
	
	$('.text-trunc').each(function(index, ele){
		console.log(ele)

		var text = $(ele).siblings('.small').text().trim() //.substring(0, 30).split(" ").slice(0, -1).join(" ") + "...";
		console.log(text)
		var actor = /^[^\s]+/.exec(text)
		console.log(actor[0])
		var rest = text.slice(actor[0].length).trim().substring(0, 20).split(" ").slice(0, -1).join(" ") + "...";
		$(ele).text(actor[0]+ ' '+rest);
	})





	$('.more_info').click(function(){
		if($(this)[0]==$('.open')[0]){
			close_panel()
			return;
		}
		// console.log($(this))
		// console.log($('.open'))

		close_panel()
		
		
		$(this).html("<a>See less</a>")
		$(this).parent().animate({'height':'400px'})
		$(this).parent().parent().animate({'height': '400px'})
		$(this).parent().parent().parent().animate({'height': '400px'})
		$(this).siblings('.text-trunc').hide()
		$(this).siblings('.small').show()
		$(this).addClass('open')
	})

	function close_panel(){
		$('.open').html('<a>See more</a>')
		$('.open').parent().animate({'height':'200px'})
		$('.open').parent().parent().animate({'height': '200px'})
		$('.open').parent().parent().parent().animate({'height': '200px'})
		$('.open').siblings('.small').hide()
		$('.open').siblings('.text-trunc').show()
		$('.open').removeClass('open')
		
	}


})