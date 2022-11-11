from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm

# Create your views here.


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("cafes/index")
    else:
        form = UserCreationForm()
        context = {"form": form}
    return render(request, "accounts/signup.html", context)


# def login(request):
#     form = AuthenticationForm()
#     context = {"form": form}
#     return render(request, "accounts/login.html", context)
