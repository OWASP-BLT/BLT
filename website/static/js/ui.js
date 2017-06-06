$(document).ready(function(){

	var prev_html = $('.user-menu .dropdown-toggle').html();
	var small_icon= false;

	$(window).resize(function()
	{
		if($(window).width()<400 && !small_icon)
		{
			small_icon = true;
			$('.user-menu .dropdown-toggle').html("<label>&#9776</label>");
			return;
		}

		if($(window).width()>400 && small_icon)
		{
			small_icon = false;
			$('.user-menu .dropdown-toggle').html(prev_html);
			return;
		}
	});

	$('.edit-pic').click(function(){
		$('.update-pic').show();
		$('.edit-pic').hide();
	});

	$("#startTour").click(function() {
	    introJs().start();
    });

});