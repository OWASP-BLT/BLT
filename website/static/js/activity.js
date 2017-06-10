$(document).ready(function(){
	
	$('.more_info').click(function(){
		
		$('.open').parent().animate({'height':'200px'})
		$('.open').parent().parent().animate({'height': '200px'})
		$('.open').parent().parent().parent().animate({'height': '200px'})
		$('.open').hide()
		$('.open').removeClass('.open')
		
		$(this).parent().animate({'height':'400px'})
		$(this).parent().parent().animate({'height': '400px'})
		$(this).parent().parent().parent().animate({'height': '400px'})
		$(this).siblings('.small').show()
		$(this).siblings('.small').addClass('open')
	})
})