from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.http import Http404
from .models import Movie, Myrating, MyList
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Case, When
import pandas as pd
import numpy as np
from .forms import RegisterForm

# Creating views functions here.

def index(request):
    movies = Movie.objects.all()
    movie=pd.DataFrame(list(Movie.objects.all().values()))
    
    query = request.GET.get('q')

# if user search any movie
    if query:
        movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'Home/index.html', {'movies': movies})

# otherwise render all the movies present in database
    return render(request, 'Home/index.html', {'movies': movies})


         
# Show details of the movie and give option to rate it and add or remove movie in the user's movie list
def detail(request, movie_id):

 #if user is not logged in or registered redirect him to login page
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404
    movies = get_object_or_404(Movie, id=movie_id)

    #get the clicked movie from movie database to show its details
    movie = Movie.objects.get(id=movie_id)
    
    temp = list(MyList.objects.all().values().filter(movie_id=movie_id,user=request.user))
    if temp:
        update = temp[0]['watch']
    else:
        update = False
    if request.method == "POST":

        # For adding and removing movies in user's movie list
        if 'watch' in request.POST:
            watch_flag = request.POST['watch']
            if watch_flag == 'on':
                update = True
            else:
                update = False
            if MyList.objects.all().values().filter(movie_id=movie_id,user=request.user):
                MyList.objects.all().values().filter(movie_id=movie_id,user=request.user).update(watch=update)
            else:
                q=MyList(user=request.user,movie=movie,watch=update)
                q.save()
            if update:
                messages.success(request, "Movie added to your list!")
            else:
                messages.success(request, "Movie removed from your list!")

            
        # For rating
        else:
            rate = request.POST['rating']
            if Myrating.objects.all().values().filter(movie_id=movie_id,user=request.user):
                Myrating.objects.all().values().filter(movie_id=movie_id,user=request.user).update(rating=rate)
            else:
                q=Myrating(user=request.user,movie=movie,rating=rate)
                q.save()

            messages.success(request, "Rating has been submitted!")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    out = list(Myrating.objects.filter(user=request.user.id).values())

    # To display ratings in the movie detail page
    movie_rating = 0
    rate_flag = False
    for each in out:
        if each['movie_id'] == movie_id:
            movie_rating = each['rating']
            rate_flag = True
            break

    context = {'movies': movies,'movie_rating':movie_rating,'rate_flag':rate_flag,'update':update}
    return render(request, 'Home/detail.html', context)


# MyList functionality
def watch(request):
    #if user is not logged in or registered
    if not request.user.is_authenticated:
        return redirect("login")
        
    if not request.user.is_active:
        raise Http404

    movies = Movie.objects.filter(mylist__watch=True,mylist__user=request.user)
    query = request.GET.get('q')
 
    if query:
        movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'Home/watch.html', {'movies': movies})

    return render(request, 'Home/watch.html', {'movies': movies})


# To get similar movies based on user rating
# To get similar movies based on user rating
# Function to predict ratings
def get_similar(movie_name,rating,corrMatrix):
    Pred_ratings = corrMatrix[movie_name]*(rating-2.5)
    Pred_ratings = Pred_ratings.sort_values(ascending=False)
    return Pred_ratings

# Recommendation Algorithm
def recommend(request):

    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404


    ratings=pd.DataFrame(list(Myrating.objects.all().values()))

    new_user=ratings.user_id.unique().shape[0]
    current_user_id= request.user.id

	# if new user not rated any movie
    if current_user_id>new_user:
        movie=Movie.objects.get(id=10)
        q=Myrating(user=request.user,movie=movie,rating=0)
        q.save()


    ratingTable = ratings.pivot_table(index=['user_id'],columns=['movie_id'],values='rating')
    
    ratingTable = ratingTable.fillna(0,axis=1)

    #making a correlation similarity matrix of movies
    corrMatrix = ratingTable.corr(method='pearson')
    print(corrMatrix)

    curr_user = pd.DataFrame(list(Myrating.objects.filter(user=request.user).values())).drop(['user_id','id'],axis=1)

  #getting list of movie ids and ratings of movie already rated by user
    user_filtered = [tuple(x) for x in curr_user.values]
	
	#getting movie ids of the already rated movies by the user
    movie_id_watched = [each[0] for each in user_filtered]

    similar_movies = pd.DataFrame()
    for movie,rating in user_filtered:
        similar_movies = similar_movies.append(get_similar(movie,rating,corrMatrix),ignore_index = True)

	#sorting in descending order of ratings of movies
    movies_id = list(similar_movies.sum().sort_values(ascending=False).index)

#taking the movie ids from the 'movies_id' which is not rated by user
    movies_id_recommend = [each for each in movies_id if each not in movie_id_watched]
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(movies_id_recommend)])

#getting ten recommended movies
    movie_list=list(Movie.objects.filter(id__in = movies_id_recommend).order_by(preserved)[:10])

    context = {'movie_list': movie_list}
    return render(request, 'Home/recommend.html', context)







# Register user
def signup(request): 
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db() 

            #get username and password of the user
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1') 
           #save the users data
            user.save()
            
 
            # login user after signing up
            user = authenticate(username=username, password=password)
            login(request, user)
 
            # redirect user to home page
            return redirect('index')
    else:
        # render the file with blank form
        form = RegisterForm()
    return render(request, 'Home/signup.html', {'form': form})     
 


   



   

# Login User
def Login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("index")
            else:
                return render(request, 'Home/login.html', {'error_message': 'Your account disable'})
        else:
            return render(request, 'Home/login.html', {'error_message': 'Invalid Login'})

    return render(request, 'Home/login.html')


# Logout user
def Logout(request):
    logout(request)
    return redirect("login")



