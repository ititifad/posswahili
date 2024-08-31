
$(document).ready(function() {
    // Fade out messages after 5 seconds
    setTimeout(function() {
        $('.messages').fadeOut('slow');
    }, 5000);

    // Example of dynamic form field addition
    $('#add-item-btn').click(function() {
        var newItem = $('.item-row:first').clone();
        newItem.find('input').val('');
        $('#items-container').append(newItem);
    });

    // Example of AJAX form submission
    $('#ajax-form').submit(function(e) {
        e.preventDefault();
        $.ajax({
            url: $(this).attr('action'),
            type: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                alert('Ombi limetumwa kwa mafanikio!');
            },
            error: function() {
                alert('Kuna hitilafu imetokea. Tafadhali jaribu tena.');
            }
        });
    });
});