$(document).ready(function(){
	
	$('.more_info').click(function(){
		if($(this)[0]==$('.open')[0]){
			close_panel()
			return;
		}
		console.log($(this))
		console.log($('.open'))

		close_panel()
		
		
		$(this).html("<a>See less</a>")
		$(this).parent().animate({'height':'400px'})
		$(this).parent().parent().animate({'height': '400px'})
		$(this).parent().parent().parent().animate({'height': '400px'})
		$(this).siblings('.small').show()
		$(this).addClass('open')
	})

	function close_panel(){
		$('.open').html('<a>See more</a>')
		$('.open').parent().animate({'height':'200px'})
		$('.open').parent().parent().animate({'height': '200px'})
		$('.open').parent().parent().parent().animate({'height': '200px'})
		$('.open').siblings('.small').hide()
		$('.open').removeClass('open')
		
	}
})